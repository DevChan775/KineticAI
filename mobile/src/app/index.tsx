import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, TouchableOpacity } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const cameraRef = useRef<CameraView>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // 카메라 권한 확인 및 요청
    if (!permission?.granted) {
      requestPermission();
    }

    // 백엔드 파이썬 FastAPI 웹소켓 연결
    // 주의: 모바일 기기나 에뮬레이터에서는 localhost 대신 실제 컴퓨터 IPv4 주소를 입력해야함
    const socket = new WebSocket('ws://자신의IP주소:8000/ws/video');
    wsRef.current = socket;

    socket.onopen = () => {
      console.log('서버와 연결 성공!');
    };

    socket.onmessage = (e: MessageEvent) => {
      try {
        const result = JSON.parse(e.data);
        console.log('AI 피드백:', result.feedback);
      } catch (err) {
        console.log('메시지 파싱 에러:', err);
      }
    };

    return () => {
      socket.close();
    };
  }, [permission]);

  // 카메라 프레임 캡처 및 웹소켓 전송 함수
  const sendFrame = async () => {
    if (cameraRef.current && wsRef.current && wsRef.current.readyState === 1) { // 1 = WebSocket.OPEN
      try {
        // await는 외부장치와 작업할 때만 주로 씀. 
        // 컴퓨터 CPU가 혼자 할 수 없고, 외부 장치나 네트워크에 부탁해야 하는 작업들은 시간이 꽤 걸림 -> 추후에 공부
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.2,
          base64: true,
        });

        if (photo?.base64) {
          wsRef.current.send(photo.base64);
        }
      } catch (error) {
        console.log('프레임 전송 에러:', error);
      }
    }
  };

  // 촬영 상태에 따른 주기적 프레임 전송
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        sendFrame();
      }, 200); // 0.2초마다 전송
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording]);
  
  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.infoText}>카메라 권한이 필요합니다.</Text>
        <TouchableOpacity style={styles.permButton} onPress={requestPermission}>
          <Text style={styles.buttonText}>권한 허용하기</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView 
        style={styles.camera} 
        facing="front" 
        ref={cameraRef}
      >
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[styles.button, { backgroundColor: isRecording ? '#E53E3E' : '#3182CE' }]}
            onPress={() => setIsRecording(!isRecording)}
          >
            <Text style={styles.buttonText}>
              {isRecording ? '촬영 중지' : '촬영 시작'}
            </Text>
          </TouchableOpacity>
        </View>
      </CameraView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  camera: { flex: 1, justifyContent: 'flex-end', alignItems: 'center' },
  buttonContainer: { marginBottom: 50 },
  button: { paddingVertical: 15, paddingHorizontal: 30, borderRadius: 10 },
  permButton: { marginTop: 15, padding: 12, backgroundColor: '#3182CE', borderRadius: 8 },
  buttonText: { fontSize: 18, color: 'white', fontWeight: 'bold' },
  infoText: { fontSize: 16, color: '#333' },
});