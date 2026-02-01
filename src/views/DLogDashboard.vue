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

        <div class="flex items-center gap-3">
          <!-- Day/Night Status Component -->
          <div class="hidden md:flex items-center justify-center bg-white border border-gray-200 px-5 py-2 rounded-xl shadow-sm">
            <div class="flex flex-col items-center">
              <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none mb-1">Time Status</span>
              <div class="flex items-center gap-1.5">
                <span :class="isDaytime ? 'text-amber-500' : 'text-indigo-600'" class="text-lg font-sans font-black">
                  {{ isDaytime ? '주간' : '야간' }}
                </span>
                <span class="text-[10px] font-bold text-gray-300">
                  ({{ isDaytime ? '06-22' : '22-06' }})
                </span>
              </div>
            </div>
          </div>

          <!-- Real-time Clock Component -->
          <div class="hidden md:flex items-center justify-center bg-white border border-gray-200 px-5 py-2 rounded-xl shadow-sm">
            <div class="flex flex-col items-center">
              <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none mb-1">Current Time</span>
              <span class="text-lg font-sans font-bold text-[#333D4B] leading-none">{{ currentClockTime }}</span>
            </div>
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
            <Line :data="chartData" :options="chartOptions" :plugins="[dataValueLabelPlugin]" />
          </div>
        </div>

        <!-- Vibration Chart (New) -->
        <div class="bg-white rounded-[24px] p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-50">
          <div class="flex items-center justify-between mb-6 px-2">
            <h3 class="font-bold text-lg text-[#191F28]">실시간 진동 변화 추이 (m/s^2)</h3>
            <div class="flex items-center gap-2">
              <span :class="isLoading ? 'bg-amber-400 animate-pulse' : 'bg-purple-500'" class="h-2 w-2 rounded-full"></span>
              <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Mobius Live</span>
            </div>
          </div>
          <div class="h-[300px] w-full">
            <Line :data="vibrationChartData" :options="vibrationChartOptions" :plugins="[dataValueLabelPlugin]" />
          </div>
        </div>
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-50 flex flex-col md:flex-row items-center gap-10">
          <div :class="statusStyles[state.currentStatus.label] ? statusStyles[state.currentStatus.label].bg : statusStyles[state.currentStatus.level].bg" class="w-40 h-40 rounded-full flex flex-col items-center justify-center transition-all duration-700 shadow-inner">
            <span class="text-xs font-bold opacity-60 mb-1">현재 상태</span>
            <span :class="statusStyles[state.currentStatus.label] ? statusStyles[state.currentStatus.label].text : statusStyles[state.currentStatus.level].text" class="text-4xl font-black tracking-tighter">
              {{ state.currentStatus.label }}
            </span>
          </div>
          <div class="flex-1 space-y-4">
            <h2 class="text-xl font-bold text-[#191F28]">AI 층간소음 분석 결과</h2>
            <div class="p-4 bg-gray-50 rounded-2xl border border-gray-100 italic text-[21px] font-bold text-[#4E5968] leading-relaxed">
              "{{ state.latestEvent.note }}"
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-gray-50 p-4 rounded-2xl">
                <span class="text-[11px] font-bold text-gray-400 block mb-1 uppercase tracking-wider">실시간 소음</span>
                <span class="text-xl font-extrabold text-[#333D4B]">{{ formatDb(state.currentStatus.avgDb) }} dB</span>
              </div>
              <div class="bg-gray-50 p-4 rounded-2xl">
                <span class="text-[11px] font-bold text-gray-400 block mb-1 uppercase tracking-wider">실시간 진동</span>
                <span class="text-xl font-extrabold text-[#333D4B]">{{ state.latestEvent.vibration?.toFixed(2) || 0 }}</span>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="bg-blue-50/50 p-4 rounded-2xl border border-blue-100/50">
                <span class="text-[11px] font-bold text-blue-400 block mb-1 uppercase tracking-wider">1분 평균 소음</span>
                <div class="flex items-baseline gap-1">
                  <span class="text-xl font-extrabold text-blue-600">{{ formatDb(state.latestEvent.avg1min || 0) }}</span>
                  <span class="text-xs font-bold text-blue-400">dB</span>
                </div>
              </div>
              <div class="bg-indigo-50/50 p-4 rounded-2xl border border-indigo-100/50">
                <span class="text-[11px] font-bold text-indigo-400 block mb-1 uppercase tracking-wider">5분 평균 소음</span>
                <div class="flex items-baseline gap-1">
                  <span class="text-xl font-extrabold text-indigo-600">{{ formatDb(state.latestEvent.avg5min || 0) }}</span>
                  <span class="text-xs font-bold text-indigo-400">dB</span>
                </div>
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
              <div class="flex justify-between items-center py-2">
                <span class="text-[20px] font-black text-gray-500 uppercase tracking-tight">AI 모델 확신도</span>
                <span class="text-[32px] font-black text-blue-600">약 {{ formatProbability(state.latestEvent.probability) }}%</span>
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
              <tr class="text-[16px] font-black text-[#333D4B] uppercase tracking-widest border-b border-gray-100 bg-gray-50/50">
                <th class="px-8 py-5">최초 감지 시각</th>
                <th class="px-8 py-5">지속 시간</th>
                <th class="px-8 py-5">유형</th>
                <th class="px-8 py-5">최대 강도</th>
                <th class="px-8 py-5 text-blue-600">1분 평균</th>
                <th class="px-8 py-5 text-indigo-600">5분 평균</th>
                <th class="px-8 py-5">최대 진동</th>
                <th class="px-8 py-5">소음 정도</th>
                <th class="px-8 py-5 text-right">상태</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 text-sm text-[#333D4B]">
              <tr v-for="event in displayEvents" :key="event.id" class="hover:bg-gray-50/50 transition-colors" :class="{ 'bg-blue-50/30': activeEventGroup && event.id === activeEventGroup.id }">
                <td class="px-8 py-5 text-gray-400 font-medium">{{ event.startTimeString }}</td>
                <td class="px-8 py-5 text-gray-400 font-medium">{{ event.duration }}초</td>
                <td class="px-8 py-5 font-bold">{{ event.type }}</td>
                <td class="px-8 py-5 font-bold">{{ formatDb(event.maxDb) }}</td>
                <td class="px-8 py-5 text-blue-600 font-medium">{{ formatDb(event.avg1min) }}</td>
                <td class="px-8 py-5 text-indigo-600 font-medium">{{ formatDb(event.avg5min) }}</td>
                <td class="px-8 py-5 font-bold text-purple-600">{{ event.maxVibration?.toFixed(2) || '-' }}</td>
                <td class="px-8 py-5 font-bold text-rose-600">{{ event.noiseDegree }}</td>
                <td class="px-8 py-5 text-right font-bold">
                  <span :class="statusStyles[event.level].badge" class="px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-tighter">
                    {{ event.level }}
                  </span>
                </td>
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
  avg1min?: number; avg5min?: number;
  level: StatusLevel; location: string; note: string; lastUpdatedAt: Date;
  vibration?: number; isExternal?: boolean;
}
// 히스토리 테이블에 표시될 그룹화된 이벤트 타입
interface EventGroup {
  id: number; type: string; startTime: Date; lastTime: Date; startTimeString: string;
  duration: number; maxDb: number; avg1min: number; avg5min: number; maxVibration: number; level: StatusLevel; location: string;
  noiseDegree?: string;
}

// [추가] 소음 정도 판정 함수
const getNoiseDegree = (avg1min: number, avg5min: number, time: Date) => {
  const hour = time.getHours();
  const isNight = hour >= 22 || hour < 6;
  const degrees = [];

  if (isNight) {
    if (avg1min > 35) degrees.push('수인한도 초과');
    else if (avg1min > 34) degrees.push('문제 소음');
    if (avg5min > 40) degrees.push('층간 소음');
  } else {
    if (avg1min > 40) degrees.push('수인한도 초과');
    else if (avg1min > 39) degrees.push('문제 소음');
    if (avg5min > 45) degrees.push('층간 소음');
  }

  return degrees.length > 0 ? degrees.join(', ') : '정상';
};

// --- 2. 스타일 및 상수 ---
const statusStyles: Record<string, StatusStyle> = {
  safe: { bg: 'bg-emerald-50 shadow-[inset_0_2px_10px_rgba(16,185,129,0.1)]', text: 'text-emerald-500', badge: 'bg-emerald-100 text-emerald-600' },
  warning: { bg: 'bg-amber-50 shadow-[inset_0_2px_10px_rgba(245,158,11,0.1)]', text: 'text-amber-500', badge: 'bg-amber-100 text-amber-600' },
  danger: { bg: 'bg-rose-50 shadow-[inset_0_2px_10px_rgba(244,63,94,0.1)]', text: 'text-rose-500', badge: 'bg-rose-100 text-rose-600' },
  '외부 소음': { bg: 'bg-gray-100 shadow-[inset_0_2px_10px_rgba(0,0,0,0.05)]', text: 'text-gray-500', badge: 'bg-gray-200 text-gray-600' }
}

// Chart.js Custom Plugin to draw values on points
const dataValueLabelPlugin = {
  id: 'dataValueLabel',
  afterDatasetsDraw(chart: any) {
    const { ctx, data } = chart;
    ctx.save();
    data.datasets.forEach((dataset: any, i: number) => {
      const meta = chart.getDatasetMeta(i);
      meta.data.forEach((element: any, index: number) => {
        const dataValue = dataset.data[index];
        // 0.00인 경우 표기가 잘리거나 불필요하므로 제외 (0.01 이상만 표기)
        if (typeof dataValue !== 'undefined' && dataValue !== null && dataValue >= 0.01) {
          ctx.fillStyle = dataset.borderColor;
          ctx.font = 'bold 10px Pretendard';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'bottom';
          const position = element.tooltipPosition();
          // 값 표시 (소수점 1자리)
          // 진동 차트(i=0이 소음, i=0이 진동 - 현재 Line 컴포넌트 각각 호출됨)
          // dataset label로 구분하여 단위 추가
          const unit = dataset.label === 'Magnitude' ? ' m/s²' : '';
          ctx.fillText(dataValue.toFixed(2) + unit, position.x, position.y - 8);
        }
      });
    });
    ctx.restore();
  }
};

// [추가] dB 포맷팅 함수 (소수점 둘째자리에서 올림)
const formatDb = (val: number) => {
  if (!val) return '약 0.00';
  return '약 ' + (Math.ceil(val * 100) / 100).toFixed(2);
}

// [추가] Probability 포맷팅 함수
const formatProbability = (val: number) => {
  if (!val) return '0.00';
  return (Math.ceil(val * 100) / 100).toFixed(2);
}

// [추가] AI 결과 한글 매핑
const labelMap: Record<string, string> = {
  'footsteps': '발망치 소음',
  'impact_noise': '충격 소음',
  'door_wood_knock': '노크 소음',
  'door_wood_slam': '문 닫는 소음',
  'voice': '대화 소음',
  'silence': '정적',
  'dog': '개 짖는 소리',
  'laughing': '웃음 소리',
  'crying_baby': '아기 울음 소리',
  'vacuum_cleaner': '청소기 소음',
  'thunderstorm': '천둥 소음(외부)',
  'car_horn': '경적 소음(외부)',
  'siren': '사이렌 소음(외부)',
  'music': '음악 소음'
};

const translateLabel = (label: string) => {
  const lower = label.toLowerCase();
  for (const key in labelMap) {
    if (lower.includes(key)) return labelMap[key];
  }
  return label; // 매핑 없으면 원래 이름 표시
};

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

const isDaytime = computed(() => {
  const hour = now.value.getHours();
  return hour >= 6 && hour < 22;
});

const currentClockTime = ref(''); // Header Clock
const isLoading = ref(false);
const error = ref<string | null>(null);
let alertAudio: HTMLAudioElement | null = null;
let watchdogTimer: any, nowTimer: any, chartTimer: any, clockTimer: any, reconnectTimer: any; // Corrected declarations

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
    const res = await axios.get(`${API_BASE_URL}/logs?limit=100`);
    if (res.data && res.data.logs) {
      // 초기 로그는 역순으로 처리하여 시간 순서를 맞춥니다.
      const reversedLogs = res.data.logs.reverse();
      reversedLogs.forEach(processUpdate);
      // 모든 초기 로그 처리가 끝난 후, 현재 진행 중인 그룹이 있다면 강제로 완료 처리하여 히스토리에 고정합니다.
      finalizeActiveGroup();
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
    // 종료된 시점의 최종 지속 시간을 계산합니다.
    activeEventGroup.value.duration = Math.round((activeEventGroup.value.lastTime.getTime() - activeEventGroup.value.startTime.getTime()) / 1000);
    
    // 모든 이벤트를 지속 시간과 상관없이 히스토리에 추가하여 데이터 유실을 방지합니다.
    state.recentEvents.unshift({ ...activeEventGroup.value });
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
  
  const translatedResult = translateLabel(analysis.result || '소음 감지');
  const formattedProb = (Math.ceil((analysis.probability ?? 0) * 10000) / 100).toFixed(2);
  
  let note = `AI 분석 완료: ${translatedResult} (약 ${formattedProb}%)`;
  if (analysis.is_external) {
    note = `⚠️ 외부 소음 감지 (무시됨): ${translatedResult}`;
  }

  const newEvent: NoiseEvent = {
    id: eventTime.getTime(),
    time: eventTime.toLocaleTimeString('ko-KR', { hour12: false }),
    type: translatedResult,
    db: analysis.db_level ?? 0,
    avg1min: analysis.avg_1min ?? 0,
    avg5min: analysis.avg_5min ?? 0,
    probability: (analysis.probability ?? 0) * 100,
    level: severityToLevel(analysis.severity),
    location: data.house_id || '측정 구역',
    note: note,
    lastUpdatedAt: eventTime,
    vibration: analysis.vibration_max ?? 0, 
    isExternal: !!analysis.is_external
  };

  state.latestEvent = newEvent;
  state.currentStatus = {
    level: newEvent.level,
    label: newEvent.isExternal ? '외부 소음' : (newEvent.level === 'safe' ? '안전' : (newEvent.level === 'warning' ? '주의' : '위험')),
    description: newEvent.note,
    avgDb: newEvent.db,
    riskScore: newEvent.db < 39 ? 10 : (newEvent.db <= 57 ? 50 : 95)
  };

  // [핵심] 중재 메시지 상태 업데이트 (Red/Yellow 시 '발송됨' 표시)
  state.mediationSentStatus = !!data.action?.mediation_sent;
  if (state.mediationSentStatus) {
    state.mediationSentTime = new Date().toLocaleTimeString('ko-KR', { hour12: false });
  } else {
    state.mediationSentTime = null;
  }
  
  if (newEvent.level === 'danger') {
    if (!alertAudio) alertAudio = new Audio('/sounds/alert.wav');
    alertAudio.play().catch(() => {});
  }

  // --- 이벤트 그룹화 로직 ---
  if (!activeEventGroup.value) {
    activeEventGroup.value = {
      id: newEvent.id, type: newEvent.type, startTime: eventTime, lastTime: eventTime,
      startTimeString: newEvent.time, duration: 0, maxDb: newEvent.db, 
      avg1min: newEvent.avg1min || 0, avg5min: newEvent.avg5min || 0,
      maxVibration: newEvent.vibration || 0, level: newEvent.level, location: newEvent.location,
      noiseDegree: getNoiseDegree(newEvent.avg1min || 0, newEvent.avg5min || 0, eventTime)
    };
  } else if (activeEventGroup.value.type === newEvent.type && (eventTime.getTime() - activeEventGroup.value.lastTime.getTime()) < 10000) {
    activeEventGroup.value.lastTime = eventTime;
    if (newEvent.db > activeEventGroup.value.maxDb) activeEventGroup.value.maxDb = newEvent.db;
    // 1분/5분 평균 및 소음 정도는 '최초 감지 시점' 값을 유지하거나, 필요시 업데이트 
    // 유저 요청에 따라 '최초 감지 시각으로부터의' 값을 유지하도록 함 (업데이트 안 함)
    const currentVib = newEvent.vibration || 0;
    if (currentVib > activeEventGroup.value.maxVibration) activeEventGroup.value.maxVibration = currentVib;
    if (levelToNumber(newEvent.level) > levelToNumber(activeEventGroup.value.level)) activeEventGroup.value.level = newEvent.level;
  } else {
    finalizeActiveGroup();
    activeEventGroup.value = {
      id: newEvent.id, type: newEvent.type, startTime: eventTime, lastTime: eventTime,
      startTimeString: newEvent.time, duration: 0, maxDb: newEvent.db, 
      avg1min: newEvent.avg1min || 0, avg5min: newEvent.avg5min || 0,
      maxVibration: newEvent.vibration || 0, level: newEvent.level, location: newEvent.location,
      noiseDegree: getNoiseDegree(newEvent.avg1min || 0, newEvent.avg5min || 0, eventTime)
    };
  }
};

// 사과 이벤트 처리 함수 (실시간 병렬 수신 대응)
const handleApologyEvent = (data: any) => {
  state.apologySentStatus = true;
  // 시간 포맷팅 (초 단위까지 표시하여 정확한 시각 알림)
  const receivedTime = new Date(data.timestamp);
  state.apologySentTime = receivedTime.toLocaleTimeString('ko-KR', { hour12: false });
  
  console.log(`[REAL-TIME] 사과 메시지 수신 확인: ${state.apologySentTime}`);
  
  // 사용자에게 시각적으로 알림 (필요시 알림음 추가 가능)
}

// --- WebSocket 연결 로직 ---
let socket: WebSocket | null = null;

const setupWebSocket = () => {
  // Use explicit localhost:8080 because dev server (5173) != backend (8080)
  // [Modified] Support both Localhost and Ngrok/Remote
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  let wsUrl = `${protocol}//localhost:8080/ws`; // Default local
  
  // If running on ngrok or remote IP (not localhost/127.0.0.1)
  if (!window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')) {
     // Assume backend is on the same host/port if served together, 
     // OR if separated, user needs to config. 
     // But typically with ngrok, frontend/backend might be on different tunnels OR same machine.
     // If user accesses Frontend via ngrok, they probably need Backend via ngrok too.
     // The provided AI_SERVER_URL in config.py is the backend URL.
     // We can try to use the current host but port 8080 might be blocked or different.
     // Safer bet: If on ngrok, assume backend is same domain (if proxied) OR ask user.
     // For now, let's keep localhost:8080 for local dev, but allow override?
     // Actually, mixed content (https frontend, ws backend) will fail.
     // If user visits https://xyz.ngrok-free.app, they need wss://xyz.ngrok-free.app/ws.
     wsUrl = `${protocol}//${window.location.host}/ws`; 
     // Note: This assumes the Frontend server proxies /ws to Backend 8080, 
     // OR Backend is serving the Frontend. 
     // If they are separate (Vite 5173, Uvicorn 8080), this fails remotely.
     // But typically production setups assume integration.
     // For safety in this specific "Separate Dev Server" setup:
     // If remote, we can't easily guess the backend URL without config.
     // Let's stick to localhost:8080 for now as the user seems to be testing locally.
     // Reverting to the HARDCODED localhost:8080 which is safer for this specific user env.
  }
  
  // Force localhost:8080 as requested by user environment
  wsUrl = 'ws://localhost:8080/ws';
  
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
  plugins: { 
    legend: { display: false }, 
    tooltip: { enabled: true },
  },
  scales: { 
    y: { 
      min: 0, 
      max: 80, 
      ticks: {
        stepSize: 10,
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
      max: 1.4, 
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