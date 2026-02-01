<template>
  <div id="report-area" class="min-h-screen bg-[#F9FAFB] font-sans text-[#191F28] p-4 md:p-10">
    <div class="max-w-6xl mx-auto space-y-6">
      
      <header class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="px-2 py-1 bg-blue-100 text-blue-600 text-[10px] font-bold rounded-md uppercase tracking-tighter">Evidence Center</span>
            <h1 class="text-2xl font-bold text-[#191F28] tracking-tight">{{ buildingName }}</h1>
          </div>
          <p class="text-[#4E5968] font-medium text-sm">{{ unitName }} · 실시간 소음 관제 및 증거 수집</p>
        </div>

        <!-- Real-time Clock Component -->
        <div class="hidden md:flex items-center justify-center bg-white border border-gray-200 px-5 py-2 rounded-xl shadow-sm">
          <div class="flex flex-col items-center">
            <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none mb-1">Current Time</span>
            <span class="text-lg font-mono font-bold text-[#333D4B] leading-none">{{ currentClockTime }}</span>
          </div>
        </div>
        
        <div class="flex items-center gap-2 no-print">
          <button @click="exportToCSV" class="flex items-center gap-2 bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 px-4 py-2.5 rounded-xl text-sm font-bold transition-all shadow-sm">
            <TableCellsIcon class="h-4 w-4 text-gray-400" />
            CSV 추출
          </button>
          <button @click="exportToPDF" class="flex items-center gap-2 bg-[#3182F6] hover:bg-[#1B64DA] text-white px-4 py-2.5 rounded-xl text-sm font-bold transition-all shadow-md">
            <DocumentArrowDownIcon class="h-4 w-4" />
            PDF 리포트 생성
          </button>
        </div>
      </header>

      <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Noise Chart -->
        <div class="bg-white rounded-[24px] p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-50">
          <div class="flex items-center justify-between mb-6 px-2">
            <h3 class="font-bold text-lg text-[#191F28]">실시간 소음 변화 추이 (dB)</h3>
            <div class="flex items-center gap-2">
              <span :class="isLoading ? 'bg-amber-400 animate-pulse' : 'bg-green-500'" class="h-2 w-2 rounded-full"></span>
              <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Mobius Live</span>
            </div>
          </div>
          <div class="h-[300px] w-full">
            <Line :data="chartData" :options="chartOptions" />
          </div>
        </div>

        <!-- Vibration Chart (New) -->
        <div class="bg-white rounded-[24px] p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-50">
          <div class="flex items-center justify-between mb-6 px-2">
            <h3 class="font-bold text-lg text-[#191F28]">실시간 진동 변화 추이 (Magnitude)</h3>
            <div class="flex items-center gap-2">
              <span :class="isLoading ? 'bg-amber-400 animate-pulse' : 'bg-purple-500'" class="h-2 w-2 rounded-full"></span>
              <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Mobius Live</span>
            </div>
          </div>
          <div class="h-[300px] w-full">
            <Line :data="vibrationChartData" :options="vibrationChartOptions" />
          </div>
        </div>
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-50 flex flex-col md:flex-row items-center gap-10">
          <div :class="statusStyles[state.currentStatus.level].bg" class="w-40 h-40 rounded-full flex flex-col items-center justify-center transition-all duration-700 shadow-inner">
            <span class="text-xs font-bold opacity-60 mb-1">현재 상태</span>
            <span :class="statusStyles[state.currentStatus.level].text" class="text-4xl font-black tracking-tighter">
              {{ state.currentStatus.label }}
            </span>
          </div>
          <div class="flex-1 space-y-4">
            <h2 class="text-xl font-bold text-[#191F28]">AI 층간소음 분석 결과</h2>
            <div class="p-4 bg-gray-50 rounded-2xl border border-gray-100 italic text-sm text-[#4E5968]">
              "{{ state.latestEvent.note }}"
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div class="bg-gray-50 p-4 rounded-2xl">
                <span class="text-[11px] font-bold text-gray-400 block mb-1 uppercase tracking-wider">Instant dB</span>
                <span class="text-xl font-extrabold text-[#333D4B]">{{ state.currentStatus.avgDb }} dB</span>
              </div>
              <div class="bg-gray-50 p-4 rounded-2xl">
                <span class="text-[11px] font-bold text-gray-400 block mb-1 uppercase tracking-wider">Instant Vib.</span>
                <span class="text-xl font-extrabold text-[#333D4B]">{{ state.latestEvent.vibration?.toFixed(2) || 0 }}</span>
              </div>
              <div class="bg-gray-50 p-4 rounded-2xl">
                <span class="text-[11px] font-bold text-gray-400 block mb-1 uppercase tracking-wider">Risk Index</span>
                <span class="text-xl font-extrabold text-[#333D4B]">{{ state.currentStatus.riskScore }} %</span>
              </div>
            </div>
            
            <div class="pt-4 border-t border-gray-50 grid grid-cols-2 gap-4">
              <div class="space-y-1">
                <p class="text-[11px] font-bold text-gray-400 uppercase tracking-wider">중재 메시지</p>
                <p v-if="state.mediationSentStatus" class="text-sm font-bold text-blue-600">발송됨</p>
                <p v-else class="text-sm font-medium text-gray-500">대기중</p>
                <p v-if="state.mediationSentTime" class="text-xs text-gray-400">{{ state.mediationSentTime }}</p>
              </div>
              <div class="space-y-1">
                <p class="text-[11px] font-bold text-gray-400 uppercase tracking-wider">사과 메시지</p>
                <p v-if="state.apologySentStatus" class="text-sm font-bold text-blue-600">발송됨</p>
                <p v-else class="text-sm font-medium text-gray-500">대기중</p>
                <p v-if="state.apologySentTime" class="text-xs text-gray-400">{{ state.apologySentTime }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-[24px] p-7 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-50 flex flex-col justify-between">
          <div class="space-y-4">
            <h3 class="text-xs font-bold text-gray-400 mb-4 uppercase tracking-widest leading-none">Latest Detection</h3>
            <div>
              <p class="text-2xl font-black text-[#191F28]">{{ state.latestEvent.type }}</p>
              <p class="text-sm text-blue-500 font-bold">{{ state.latestEvent.location }}</p>
            </div>
            <div class="pt-4 border-t border-gray-50">
              <div class="flex justify-between text-xs mb-1 font-bold">
                <span class="text-gray-400 tracking-tighter uppercase">Probability</span>
                <span class="text-[#333D4B]">{{ state.latestEvent.probability }}%</span>
              </div>
              <div class="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
                <div class="bg-blue-500 h-full transition-all duration-1000" :style="{ width: state.latestEvent.probability + '%' }"></div>
              </div>
            </div>
          </div>
          <p v-if="error" class="text-[10px] text-red-500 mt-4 italic font-medium">{{ error }}</p>
        </div>
      </section>

      <section class="bg-white rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-50 overflow-hidden">
        <div class="px-8 py-6 border-b border-gray-50">
          <h3 class="font-bold text-lg text-[#191F28]">증거 수집 히스토리 <span class="text-xs font-normal text-gray-300 ml-2 italic">Captured Records</span></h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left">
            <thead>
              <tr class="text-[11px] font-bold text-gray-400 uppercase tracking-widest border-b border-gray-50 bg-gray-50/30">
                <th class="px-8 py-4">최초 감지 시각</th>
                <th class="px-8 py-4">지속 시간</th>
                <th class="px-8 py-4">유형</th>
                <th class="px-8 py-4 font-mono">최대 강도(dB)</th>
                <th class="px-8 py-4 font-mono">최대 진동</th>
                <th class="px-8 py-4 text-right">상태</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 text-sm text-[#333D4B]">
              <tr v-for="event in displayEvents" :key="event.id" class="hover:bg-gray-50/50 transition-colors" :class="{ 'bg-blue-50/30': activeEventGroup && event.id === activeEventGroup.id }">
                <td class="px-8 py-5 text-gray-400 font-medium">{{ event.startTimeString }}</td>
                <td class="px-8 py-5 text-gray-400 font-medium">{{ event.duration }}초</td>
                <td class="px-8 py-5 font-bold">{{ event.type }}</td>
                <td class="px-8 py-5 font-mono font-bold">{{ event.maxDb }}</td>
                <td class="px-8 py-5 font-mono font-bold text-purple-600">{{ event.maxVibration?.toFixed(2) || '-' }}</td>
                <td class="px-8 py-5 text-right font-bold">
                  <span :class="statusStyles[event.level].badge" class="px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-tighter">
                    {{ event.level }}
                  </span>
                </td>
              </tr>
              <tr v-if="displayEvents.length === 0">
                <td colspan="6" class="px-8 py-20 text-center text-gray-400 font-medium">Mobius 데이터를 수신 중입니다...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, onMounted, onUnmounted, ref } from 'vue'
import axios from 'axios'
import { TableCellsIcon, DocumentArrowDownIcon } from '@heroicons/vue/24/solid'
import { Line } from 'vue-chartjs'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

// --- 1. 타입 정의 ---
type StatusLevel = 'safe' | 'warning' | 'danger'
interface StatusStyle { bg: string; text: string; badge: string; }
interface StatusInfo { level: StatusLevel; label: string; description: string; avgDb: number; riskScore: number; }
// Mobius에서 수신하는 원본 이벤트 타입
interface NoiseEvent {
  id: number; time: string; type: string; db: number; probability: number;
  level: StatusLevel; location: string; note: string; lastUpdatedAt: Date;
  vibration?: number; // New: Vibration Magnitude
}
// 히스토리 테이블에 표시될 그룹화된 이벤트 타입
interface EventGroup {
  id: number; type: string; startTime: Date; lastTime: Date; startTimeString: string;
  duration: number; maxDb: number; maxVibration: number; level: StatusLevel; location: string;
}

// --- 2. 스타일 및 상수 ---
const statusStyles: Record<StatusLevel, StatusStyle> = {
  safe: { bg: 'bg-emerald-50 shadow-[inset_0_2px_10px_rgba(16,185,129,0.1)]', text: 'text-emerald-500', badge: 'bg-emerald-100 text-emerald-600' },
  warning: { bg: 'bg-amber-50 shadow-[inset_0_2px_10px_rgba(245,158,11,0.1)]', text: 'text-amber-500', badge: 'bg-amber-100 text-amber-600' },
  danger: { bg: 'bg-rose-50 shadow-[inset_0_2px_10px_rgba(244,63,94,0.1)]', text: 'text-rose-500', badge: 'bg-rose-100 text-rose-600' }
}
const buildingName = '동국대학교 D-Log'
const unitName = '3140호'
const CHART_MAX_LENGTH = 15; // 점 사이 간격을 2배로 넓히기 위해 표시 개수 축소 (30 -> 15)

// --- 3. 상태 관리 ---
const state = reactive<{
  currentStatus: StatusInfo;
  latestEvent: NoiseEvent;
  recentEvents: EventGroup[]; // 완료된 이벤트 그룹 목록
  mediationSentStatus: boolean;
  mediationSentTime: string | null;
  apologySentStatus: boolean;
  apologySentTime: string | null;
  isMockDataMode: boolean;
}>({
  currentStatus: { level: 'safe', label: '준비', description: '관제 시스템을 초기화 중입니다.', avgDb: 0, riskScore: 0 },
  latestEvent: { id: 0, time: '-', type: '대기 중', db: 0, probability: 0, level: 'safe', location: '-', note: '연결 확인 중...', lastUpdatedAt: new Date(0), vibration: 0 },
  recentEvents: [],
  mediationSentStatus: false,
  mediationSentTime: null,
  apologySentStatus: false,
  apologySentTime: null,
  isMockDataMode: false,
})

const activeEventGroup = ref<EventGroup | null>(null); // 현재 진행중인 이벤트 그룹
const now = ref(new Date()); // 지속시간 계산을 위한 실시간 시간
const currentClockTime = ref(''); // Header Clock
const isLoading = ref(false);
const error = ref<string | null>(null);
let alertAudio: HTMLAudioElement | null = null;
let watchdogTimer: any, nowTimer: any, chartTimer: any, clockTimer: any; // Added clockTimer

// 실시간 차트 전용 데이터
const liveChartLabels = ref<string[]>([]);
const liveChartData = ref<number[]>([]);
const liveVibrationData = ref<number[]>([]); // New: Vibration Data

// --- 4. API 설정 ---
const API_BASE_URL = 'http://localhost:8080';

// --- 5. 데이터 처리 로직 ---
const fetchInitialLogs = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get(`${API_BASE_URL}/logs?limit=10`);
    if (res.data && res.data.logs) {
      // 초기 로그는 역순으로 처리하여 시간 순서를 맞춥니다.
      const reversedLogs = res.data.logs.reverse();
      reversedLogs.forEach(processUpdate);
      error.value = null;
    }
  } catch (err: any) {
    // 500 에러 등이 나도 로그가 없어서 그럴 수 있으므로 조용히 처리하거나 초기화
    console.warn("초기 로그 로드 실패 (데이터 없음 등):", err);
  } finally {
    isLoading.value = false;
  }
}

const severityToLevel = (sev: string): StatusLevel => {
  const s = (sev || 'green').toLowerCase();
  if (s === 'red' || s === 'danger') return 'danger';
  if (s === 'yellow' || s === 'warning') return 'warning';
  return 'safe';
}

const levelToNumber = (level: StatusLevel): number => {
  if (level === 'danger') return 2;
  if (level === 'warning') return 1;
  return 0;
}

// 진행중인 이벤트를 완료하고 히스토리에 추가
const finalizeActiveGroup = () => {
  if (activeEventGroup.value) {
    activeEventGroup.value.duration = Math.round((activeEventGroup.value.lastTime.getTime() - activeEventGroup.value.startTime.getTime()) / 1000);
    if (activeEventGroup.value.duration >= 2) {
      state.recentEvents.unshift({ ...activeEventGroup.value });
      if (state.recentEvents.length > 10) state.recentEvents.pop();
    }
  }
  activeEventGroup.value = null;
}

// WebSocket 또는 초기 데이터로부터 받은 데이터를 처리하는 메인 함수
const processUpdate = (data: any) => {
  const analysis = data.analysis || data;
  
  state.isMockDataMode = !!data.is_mock_data;

  // 'event' 키가 있으면 사과 메시지
  if (data.event && data.event === 'apology') {
    handleApologyEvent(data);
    return;
  }
  
  if (!analysis.result && typeof analysis.db_level === 'undefined') return;

  const eventTime = new Date();
  
  const note = `AI 분석 완료: ${analysis.result} (${(analysis.probability * 100).toFixed(1)}%)`;

  const newEvent: NoiseEvent = {
    id: eventTime.getTime(),
    time: eventTime.toLocaleTimeString('ko-KR', { hour12: false }),
    type: analysis.result || '소음 감지',
    db: analysis.db_level ?? 0,
    probability: (analysis.probability ?? 0) * 100,
    level: severityToLevel(analysis.severity),
    location: data.house_id || '측정 구역',
    note: note,
    lastUpdatedAt: eventTime,
    vibration: analysis.vibration_max ?? 0, // Read vibration_max
  };

  state.latestEvent = newEvent;
  state.currentStatus = {
    level: newEvent.level,
    label: newEvent.level === 'safe' ? '안전' : (newEvent.level === 'warning' ? '주의' : '위험'),
    description: `${newEvent.type} 감지 - ${newEvent.note}`,
    avgDb: newEvent.db,
    riskScore: newEvent.level === 'safe' ? 10 : (newEvent.level === 'warning' ? 45 : 95)
  };
  
  if (newEvent.level === 'danger') {
    if (!alertAudio) alertAudio = new Audio('/sounds/alert.wav');
    alertAudio.play().catch(() => {});
  }

  // --- 이벤트 그룹화 로직 ---
  if (!activeEventGroup.value) {
    activeEventGroup.value = {
      id: newEvent.id, type: newEvent.type, startTime: eventTime, lastTime: eventTime,
      startTimeString: newEvent.time, duration: 0, maxDb: newEvent.db, maxVibration: newEvent.vibration || 0, level: newEvent.level, location: newEvent.location
    };
  } else if (activeEventGroup.value.type === newEvent.type && (eventTime.getTime() - activeEventGroup.value.lastTime.getTime()) < 10000) {
    activeEventGroup.value.lastTime = eventTime;
    if (newEvent.db > activeEventGroup.value.maxDb) activeEventGroup.value.maxDb = newEvent.db;
    const currentVib = newEvent.vibration || 0;
    if (currentVib > activeEventGroup.value.maxVibration) activeEventGroup.value.maxVibration = currentVib;
    if (levelToNumber(newEvent.level) > levelToNumber(activeEventGroup.value.level)) activeEventGroup.value.level = newEvent.level;
  } else {
    finalizeActiveGroup();
    activeEventGroup.value = {
      id: newEvent.id, type: newEvent.type, startTime: eventTime, lastTime: eventTime,
      startTimeString: newEvent.time, duration: 0, maxDb: newEvent.db, maxVibration: newEvent.vibration || 0, level: newEvent.level, location: newEvent.location
    };
  }
};

// 사과 이벤트 처리 함수
const handleApologyEvent = (data: any) => {
  state.apologySentStatus = true;
  state.apologySentTime = new Date(data.timestamp).toLocaleString('ko-KR');
  console.log("Apology message received and processed!", data);
}

// --- WebSocket 연결 로직 ---
let socket: WebSocket | null = null;

const setupWebSocket = () => {
  // Use explicit localhost:8080 because dev server (5173) != backend (8080)
  const wsUrl = 'ws://localhost:8080/ws';
  
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    error.value = null;
    console.log('WebSocket connection established.');
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      processUpdate(data);
    } catch (e) {
      console.error('Error parsing WebSocket message:', e);
    }
  };

  socket.onerror = (err) => {
    console.error('WebSocket Error:', err);
    error.value = "실시간 연결에 실패했습니다. 5초 후 재연결합니다.";
  };

  socket.onclose = () => {
    console.log('WebSocket connection closed. Reconnecting in 5s...');
    socket = null; // 소켓 참조 제거
    // 5초 후 재연결 시도
    if (!reconnectTimer) {
        reconnectTimer = setTimeout(setupWebSocket, 5000);
    }
  };
}

// --- 6. UI 렌더링을 위한 Computed 속성 ---
const displayEvents = computed((): EventGroup[] => {
  const events: EventGroup[] = [];
  if (activeEventGroup.value) {
    const activeGroupForDisplay: EventGroup = {
      ...activeEventGroup.value,
      duration: Math.round((now.value.getTime() - activeEventGroup.value.startTime.getTime()) / 1000)
    };
    events.push(activeGroupForDisplay);
  }
  events.push(...state.recentEvents);
  return events;
});

// 실시간 차트 데이터
const chartData = computed(() => ({
  labels: liveChartLabels.value,
  datasets: [{
    label: 'dB',
    data: liveChartData.value,
    borderColor: '#3182F6',
    backgroundColor: 'rgba(49, 130, 246, 0.1)',
    fill: true,
    tension: 0.4,
    pointRadius: 2,
    pointBackgroundColor: '#3182F6'
  }]
}))

const vibrationChartData = computed(() => ({
  labels: liveChartLabels.value,
  datasets: [{
    label: 'Magnitude',
    data: liveVibrationData.value,
    borderColor: '#8B5CF6', // Purple for vibration
    backgroundColor: 'rgba(139, 92, 246, 0.1)',
    fill: true,
    tension: 0.4,
    pointRadius: 2,
    pointBackgroundColor: '#8B5CF6'
  }]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { enabled: true } },
  scales: { 
    y: { 
      min: 0, 
      max: 60, 
      ticks: {
        stepSize: 5,
        color: '#6B7280',
        font: { size: 10 }
      },
      grid: { color: '#F2F4F6' } 
    }, 
    x: { 
      display: true,
      grid: { display: false },
      ticks: {
        font: { size: 8 }, // 모든 라벨 표시를 위해 크기 소폭 축소
        color: '#6B7280',
        maxRotation: 0,
        autoSkip: false // 2초마다 모든 라벨 강제 표시
      }
    } 
  },
  animation: false as const,
}

const vibrationChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { enabled: true } },
  scales: { 
    y: { 
      min: 0, 
      max: 2.0, 
      ticks: {
        stepSize: 0.2,
        color: '#6B7280',
        font: { size: 10 }
      },
      grid: { color: '#F2F4F6' } 
    }, 
    x: { 
      display: true,
      grid: { display: false },
      ticks: {
        font: { size: 8 }, // 모든 라벨 표시를 위해 크기 소폭 축소
        color: '#6B7280',
        maxRotation: 0,
        autoSkip: false // 2초마다 모든 라벨 강제 표시
      }
    } 
  },
  animation: false as const,
}

// 실시간 차트 업데이트 함수
const updateLiveChart = () => {
    const newLabels = [...liveChartLabels.value];
    const newData = [...liveChartData.value];
    const newVibData = [...liveVibrationData.value];
  
    const date = new Date();
    // Format: MM:SS
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    const timeString = `${minutes}:${seconds}`;
    
    let newDbValue = 0; 
    let newVibValue = 0;

    // 마지막으로 실제 이벤트가 수신된 지 2.1초가 지나지 않았다면 실제 db값을 사용
    if (state.latestEvent.lastUpdatedAt.getTime() > 0 && new Date().getTime() - state.latestEvent.lastUpdatedAt.getTime() < 2100) {
      newDbValue = state.latestEvent.db;
      newVibValue = state.latestEvent.vibration || 0;
    }

  newLabels.push(timeString);
  newData.push(newDbValue);
  newVibData.push(newVibValue);

  if (newLabels.length > CHART_MAX_LENGTH) {
    newLabels.shift();
    newData.shift();
    newVibData.shift();
  }
  
  liveChartLabels.value = newLabels;
  liveChartData.value = newData;
  liveVibrationData.value = newVibData;
};


// --- 7. 리포트 추출 ---
const exportToCSV = async () => {
  // ... (Code as implemented in previous step, kept concise) ...
  window.location.href = `http://localhost:8080/report/csv?house_id=dgu_house_3140&start_date=2024-01-01&end_date=2024-12-31`;
};

const exportToPDF = async () => {
  window.location.href = `http://localhost:8080/report/pdf?house_id=dgu_house_3140&start_date=2024-01-01&end_date=2024-12-31`;
};


// --- 8. 라이프사이클 훅 ---
onMounted(() => {
  // 차트 데이터 초기화
  const initialTime = new Date();
  const initialLabels: string[] = [];
  const initialData: number[] = [];
  for (let i = 0; i < CHART_MAX_LENGTH; i++) {
    initialLabels.push('');
    initialData.push(0);
  }
  liveChartLabels.value = initialLabels;
  liveChartData.value = initialData;
  liveVibrationData.value = [...initialData];

  fetchInitialLogs(); 
  setupWebSocket(); 

  // 타이머 설정
  const updateClock = () => {
    currentClockTime.value = new Date().toLocaleTimeString('ko-KR', { hour12: false });
  };
  updateClock(); // Initial call
  clockTimer = setInterval(updateClock, 1000);

  chartTimer = setInterval(updateLiveChart, 2000);
  nowTimer = setInterval(() => now.value = new Date(), 1000);
  watchdogTimer = setInterval(() => {
    if (activeEventGroup.value && (new Date().getTime() - activeEventGroup.value.lastTime.getTime() > 5000)) {
      finalizeActiveGroup();
    }
  }, 5000);
})

onUnmounted(() => { 
  if (socket) {
    socket.onclose = null; 
    socket.close();
  }
  clearTimeout(reconnectTimer);
  clearInterval(watchdogTimer);
  clearInterval(nowTimer);
  clearInterval(chartTimer);
  clearInterval(clockTimer);
})
</script>

<style>
body { font-family: 'Pretendard', sans-serif; background-color: #F9FAFB; }
@media print { .no-print { display: none; } }
</style>