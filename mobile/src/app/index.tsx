import React, { useState, useEffect, useRef, useCallback } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Modal } from 'react-native';
import {Camera, useCameraDevice, useCameraPermission, useFrameOutput,} from 'react-native-vision-camera';
import { useRunOnJS, useSharedValue } from 'react-native-worklets-core';
import * as Speech from 'expo-speech';

export default function App() {
  const device = useCameraDevice('front');
  const { hasPermission, requestPermission } = useCameraPermission();

  const [isRecording, setIsRecording] = useState<boolean>(false);

  const [selectedExercise, setSelectedExercise] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string>('원하는 운동을 고르고 촬영을 시작하세요.');
  const [borderColor, setBorderColor] = useState<string>('transparent');

  const [showMannequin, setShowMannequin] = useState<boolean>(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [exerciseCount, setExerciseCount] = useState<number>(0);

  const cameraReadyRef = useRef<boolean>(false);
  const cameraStableRef = useRef<boolean>(false);
  const [cameraStable, setCameraStable] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastFrameSentAtRef = useSharedValue(0);

  const isSpeakingFeedbackRef = useRef<boolean>(false);
  const pendingCountRef = useRef<number>(0);

  useEffect(() => {
    if (!hasPermission) {
      requestPermission();
    }
  }, [hasPermission, requestPermission]);

  const convertToKorean = (num: number): string => {
    const koreanNumbers = [
      '영', '하나', '둘', '셋', '넷', '다섯', '여섯', '일곱', '여덟', '아홉',
      '열', '열하나', '열둘', '열셋', '열넷', '열다섯', '열여섯', '열일곱', '열여덟', '열아홉',
      '스물'
    ];
    return koreanNumbers[num] || num.toString();
  };

  const speakPendingCount = () => {
    if (pendingCountRef.current > 0) {
      const countText = convertToKorean(pendingCountRef.current);
      console.log(`🔔 횟수 음성 출력: ${countText}`);
      Speech.speak(countText, {
        rate: 1.0,
        pitch: 1.0,
        onDone: () => {
          pendingCountRef.current = 0;
        }
      });
    }
  };

  const handleExerciseSelect = (ex: string) => {
    if (!isRecording) {
      setSelectedExercise(ex);
      setShowMannequin(true);
    }
  };

  const connectAndRecord = () => {
    const socket = new WebSocket('ws://192.168.123.108:8000/api/video/ws/video');
    wsRef.current = socket;

    socket.onopen = () => {
      console.log('서버와 연결 성공!');
      setIsRecording(true);
      setExerciseCount(0);
      setFeedbackMsg(`${selectedExercise} 운동을 시작합니다!`);
      isSpeakingFeedbackRef.current = false;
      pendingCountRef.current = 0;
      Speech.speak('운동을 시작하세요.');
    };

    socket.onmessage = (e: MessageEvent) => {
      try {
        const result = JSON.parse(e.data);
        console.log('📨 서버 메시지:', result);

        if (result.type === 'count') {
          setExerciseCount(result.count);

          if (isSpeakingFeedbackRef.current) {
            pendingCountRef.current = result.count;
            console.log(`피드백 음성 중: 횟수 큐에 저장 (${result.count})`);
          } else {
            const countText = convertToKorean(result.count);
            console.log(`횟수 즉시 출력: ${countText}`);
            Speech.speak(countText, { rate: 1.0, pitch: 1.0 });
          }
        } else if (result.type === 'feedback') {
          isSpeakingFeedbackRef.current = true;
          setFeedbackMsg(result.feedback);
          setBorderColor(result.color);

          setTimeout(() => {
            Speech.speak(result.feedback, {
              rate: 1.0,
              pitch: 1.2,
              onDone: () => {
                isSpeakingFeedbackRef.current = false;
                console.log('✅ 피드백 음성 종료 → 대기 중인 횟수 재생');
                speakPendingCount();
              }
            });
          }, 200);
        }
      } catch (err) {
        console.log('메시지 파싱 에러:', err);
      }
    };

    socket.onclose = (e: CloseEvent) => {
      console.log(`웹소켓 종료 코드: ${e.code}, 사유: ${e.reason}`);
      setIsRecording(false);
      setFeedbackMsg('운동이 종료되었습니다.');
      setBorderColor('transparent');
      isSpeakingFeedbackRef.current = false;
      pendingCountRef.current = 0;
    };
  };

  const startRecording = () => {
    if (!selectedExercise) {
      alert('먼저 운동 종목을 선택해주세요!');
      return;
    }

    let count = 10;
    setCountdown(count);
    setFeedbackMsg('운동을 준비하세요. 10초 뒤 촬영을 시작합니다.');
    Speech.speak('운동을 준비하세요. 10초 카운트다운을 시작합니다.');

    intervalRef.current = setInterval(() => {
      count -= 1;
      setCountdown(count);

      if (count <= 3 && count > 0) {
        Speech.speak(count.toString());
      }

      if (count === 0) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setCountdown(null);

        if (cameraStableRef.current) {
          connectAndRecord();
        } else {
          setFeedbackMsg('카메라가 준비되지 않았습니다. 준비될 때까지 기다립니다...');
          const waitForReady = setInterval(() => {
            if (cameraStableRef.current) {
              clearInterval(waitForReady);
              connectAndRecord();
            }
          }, 300);
        }
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
    isSpeakingFeedbackRef.current = false;
    pendingCountRef.current = 0;
  };

  const sendFrameBufferToServer = useRunOnJS((payload: ArrayBuffer) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const bytes = new Uint8Array(payload);

    const toBinaryString = (u8: Uint8Array) => {
      const chunkSize = 0x8000; // 32KB
      let binary = '';

      for (let i = 0; i < u8.length; i += chunkSize) {
        const chunk = u8.subarray(i, i + chunkSize);
        binary += String.fromCharCode(...chunk);
      }
      
      return binary;
   };

  const base64 = globalThis.btoa ? globalThis.btoa(toBinaryString(bytes)) : '';
  if (base64) {
    wsRef.current.send(base64);
  }
}, []);

  const frameOutput = useFrameOutput({
    pixelFormat: 'rgb',
    onFrame: (frame) => {
      'worklet';

      const now = Date.now();
      if (now - lastFrameSentAtRef.value < 200) {
        return;
      }

      lastFrameSentAtRef.value = now;
      const buffer = frame.getPixelBuffer();
      sendFrameBufferToServer(buffer);
    },
  });

  useEffect(() => {
    if (!isRecording) return;
    if (!cameraReadyRef.current || !cameraStableRef.current) return;
    return () => {
      lastFrameSentAtRef.value = 0;
    };
  }, [isRecording, cameraStable, lastFrameSentAtRef]);

  return (
    <View style={styles.container}>
      <Camera
        style={styles.camera}
        device={device ?? 'front'}
        isActive={isRecording}
        outputs={[frameOutput]}
        onStarted={() => {
          console.log('카메라 준비 완료');
          cameraReadyRef.current = true;

          setTimeout(() => {
            cameraStableRef.current = true;
            setCameraStable(true);
            console.log('카메라 안정화 완료 (stable)');
          }, 700);
        }}
      />

      <View style={[
        styles.borderOverlay,
        {
          borderColor,
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          width: '100%',
          height: '100%',
          zIndex: 10,
          elevation: 10
        }
      ]}>
        <View style={styles.topSection}>
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

          <View style={styles.feedbackBox}>
            <Text style={styles.feedbackText}>
              {countdown !== null ? `준비: ${countdown}초` : feedbackMsg}
            </Text>
            {isRecording && exerciseCount > 0 && (
              <Text style={styles.countText}>
                🔔 현재 횟수: {convertToKorean(exerciseCount)}
              </Text>
            )}
          </View>
        </View>

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

      <Modal visible={showMannequin} transparent={true} animationType="fade">
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{selectedExercise} 올바른 자세 예시</Text>
            <View style={styles.mannequinPlaceholder}>
              <Text style={{ color: 'white' }}>마네킹 이미지가 들어갈 자리입니다</Text>
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
  countText: { color: '#FFD700', fontSize: 14, textAlign: 'center', fontWeight: 'bold', marginTop: 8 },
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