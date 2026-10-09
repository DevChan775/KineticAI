import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Modal } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Speech from 'expo-speech'; 

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [isRecording, setIsRecording] = useState<boolean>(false);
  
  const [selectedExercise, setSelectedExercise] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string>('원하는 운동을 고르고 촬영을 시작하세요.');
  const [borderColor, setBorderColor] = useState<string>('transparent');

  const [showMannequin, setShowMannequin] = useState<boolean>(false);
  const [countdown, setCountdown] = useState<number | null>(null);

  const cameraRef = useRef<CameraView>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
 
  useEffect(() => {
    if (!permission?.granted) {
      requestPermission();
    }
  }, [permission]);

 
  const handleExerciseSelect = (ex: string) => {
    if (!isRecording) {
      setSelectedExercise(ex);
      setShowMannequin(true); 
    }
  };

  const connectAndRecord = () => {
    const socket = new WebSocket('ws://172.20.10.12:8000/api/video/ws/video');
    wsRef.current = socket;

    socket.onopen = () => {
      console.log('서버와 연결 성공!');
      setIsRecording(true);
      setFeedbackMsg(`${selectedExercise} 운동을 시작합니다!`);
      Speech.speak("운동을 시작하세요.");
    };

    socket.onmessage = (e: MessageEvent) => {
      try {
        const result = JSON.parse(e.data);
        if (result.status === "success") {
          setFeedbackMsg(result.feedback);     
          setBorderColor(result.color);
          Speech.stop(); 
          Speech.speak(result.feedback);
        } 
      } catch (err) {
        console.log('메시지 파싱 에러:', err);
      }
    };

    socket.onclose = (e: CloseEvent) => {
    console.log(`웹소켓 종료 코드: ${e.code}, 사유: ${e.reason}`); 
    setIsRecording(false);
    setFeedbackMsg("운동이 종료되었습니다.");
    setBorderColor('transparent');
};
  };

  const startRecording = () => {
    if (!selectedExercise) {
      alert("먼저 운동 종목을 선택해주세요!");
      return;
    }

    let count = 10;
    setCountdown(count);
    setFeedbackMsg("운동을 준비하세요. 10초 뒤 촬영을 시작합니다.");
    Speech.speak("운동을 준비하세요. 10초 카운트다운을 시작합니다.");

    intervalRef.current = setInterval(() => {
      count -= 1;
      setCountdown(count);

      if (count <= 3 && count > 0) {
        Speech.speak(count.toString());
      }

      if (count === 0) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setCountdown(null);
        connectAndRecord(); 
      }
    }, 1000);
  };

  const stopRecording = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        setCountdown(null);
      }
      if (wsRef.current) {
          wsRef.current.close();
      }
      setIsRecording(false);
      Speech.stop();
      setBorderColor('transparent');
  }

  const sendFrame = async () => {
    if (cameraRef.current && wsRef.current && wsRef.current.readyState === 1) {
      try {
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

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        sendFrame();
      }, 200);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording]);
  
  if (!permission) return <View style={styles.container} />;

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
    />

    <View style={[
        styles.borderOverlay, 
        { 
          borderColor: borderColor,
          position: 'absolute', 
          top: 0, left: 0, right: 0, bottom: 0,
          width: '100%', 
          height: '100%',
          zIndex: 10,       
          elevation: 10     
        }
    ]}>
        
        <View style={styles.topSection}>
            {/* 운동 선택 버튼 */}
            <View style={styles.exerciseSelector}>
                {['풀업', '딥스', '푸쉬업', '플랭크', '사이드 런지'].map((ex) => (
                    <TouchableOpacity 
                        key={ex} 
                        style={[styles.exButton, selectedExercise === ex && styles.exButtonActive]}
                        onPress={() => handleExerciseSelect(ex)}
                        disabled={isRecording || countdown !== null} 
                    >
                        <Text style={styles.exButtonText}>{ex}</Text>
                    </TouchableOpacity>
                ))}
            </View>

            {/* 피드백 및 카운트다운 텍스트 */}
            <View style={styles.feedbackBox}>
                <Text style={styles.feedbackText}>
                  {countdown !== null ? `준비: ${countdown}초` : feedbackMsg}
                </Text>
            </View>
        </View>

        {/* 촬영 시작/중지 버튼 */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity
              style={[styles.button, { backgroundColor: isRecording || countdown !== null ? '#E53E3E' : '#3182CE' }]}
              onPress={isRecording || countdown !== null ? stopRecording : startRecording}
          >
              <Text style={styles.buttonText}>
              {isRecording ? '촬영 중지' : countdown !== null ? '준비 취소' : '촬영 시작'}
              </Text>
          </TouchableOpacity>
        </View>

    </View>
    
    {/* 3. 마네킹 예시 모달 */}
    <Modal visible={showMannequin} transparent={true} animationType="fade">
      <View style={styles.modalContainer}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>{selectedExercise} 올바른 자세 예시</Text>
          <View style={styles.mannequinPlaceholder}>
            <Text style={{color: 'white'}}>마네킹 이미지가 들어갈 자리입니다</Text>
          </View>
          <Text style={styles.modalDesc}>인공지능이 학습하기 좋도록 측면에서 촬영해 주세요.</Text>
          <TouchableOpacity style={styles.modalCloseButton} onPress={() => setShowMannequin(false)}>
            <Text style={styles.buttonText}>확인</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  </View>
);
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  camera: { flex: 1 },
  borderOverlay: { 
      flex: 1, 
      justifyContent: 'space-between', 
      alignItems: 'center',
      borderWidth: 8,
  },
  topSection: { width: '100%', paddingTop: 50, alignItems: 'center' },
  exerciseSelector: { flexDirection: 'row', justifyContent: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 20 },
  exButton: { backgroundColor: 'rgba(0,0,0,0.5)', padding: 10, borderRadius: 8 },
  exButtonActive: { backgroundColor: '#3182CE' },
  exButtonText: { color: 'white', fontWeight: 'bold' },
  feedbackBox: { backgroundColor: 'rgba(0,0,0,0.7)', padding: 15, borderRadius: 10, width: '90%' },
  feedbackText: { color: 'white', fontSize: 16, textAlign: 'center', fontWeight: 'bold' },
  buttonContainer: { marginBottom: 50 },
  button: { paddingVertical: 15, paddingHorizontal: 40, borderRadius: 30 },
  permButton: { marginTop: 15, padding: 12, backgroundColor: '#3182CE', borderRadius: 8 },
  buttonText: { fontSize: 18, color: 'white', fontWeight: 'bold' },
  infoText: { fontSize: 16, color: '#333' },
  
  modalContainer: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { width: '80%', backgroundColor: 'white', borderRadius: 15, padding: 20, alignItems: 'center' },
  modalTitle: { fontSize: 20, fontWeight: 'bold', marginBottom: 15 },
  mannequinPlaceholder: { width: 200, height: 250, backgroundColor: 'gray', justifyContent: 'center', alignItems: 'center', marginBottom: 15 },
  modalDesc: { fontSize: 14, textAlign: 'center', marginBottom: 20, color: '#555' },
  modalCloseButton: { backgroundColor: '#3182CE', paddingVertical: 10, paddingHorizontal: 30, borderRadius: 8 }
});