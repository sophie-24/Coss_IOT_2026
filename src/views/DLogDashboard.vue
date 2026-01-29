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

      <section class="bg-white rounded-[24px] p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-50">
        <div class="flex items-center justify-between mb-6 px-2">
          <h3 class="font-bold text-lg text-[#191F28]">실시간 소음 변화 추이</h3>
          <div class="flex items-center gap-2">
            <span :class="isLoading ? 'bg-amber-400 animate-pulse' : 'bg-green-500'" class="h-2 w-2 rounded-full"></span>
            <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Mobius Live</span>
          </div>
        </div>
        <div class="h-[300px] w-full">
          <Line :data="chartData" :options="chartOptions" />
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
            <h2 class="text-xl font-bold text-[#191F28]">AI 소음 분석 결과</h2>
            <div class="p-4 bg-gray-50 rounded-2xl border border-gray-100 italic text-sm text-[#4E5968]">
              "{{ state.latestEvent.note }}"
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-gray-50 p-4 rounded-2xl">
                <span class="text-[11px] font-bold text-gray-400 block mb-1 uppercase tracking-wider">Instant dB</span>
                <span class="text-xl font-extrabold text-[#333D4B]">{{ state.currentStatus.avgDb }} dB</span>
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
                <th class="px-8 py-4 text-right">상태</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 text-sm text-[#333D4B]">
              <tr v-for="event in displayEvents" :key="event.id" class="hover:bg-gray-50/50 transition-colors" :class="{ 'bg-blue-50/30': activeEventGroup && event.id === activeEventGroup.id }">
                <td class="px-8 py-5 text-gray-400 font-medium">{{ event.startTimeString }}</td>
                <td class="px-8 py-5 text-gray-400 font-medium">{{ event.duration }}초</td>
                <td class="px-8 py-5 font-bold">{{ event.type }}</td>
                <td class="px-8 py-5 font-mono font-bold">{{ event.maxDb }}</td>
                <td class="px-8 py-5 text-right font-bold">
                  <span :class="statusStyles[event.level].badge" class="px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-tighter">
                    {{ event.level }}
                  </span>
                </td>
              </tr>
              <tr v-if="displayEvents.length === 0">
                <td colspan="5" class="px-8 py-20 text-center text-gray-400 font-medium">Mobius 데이터를 수신 중입니다...</td>
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
}
// 히스토리 테이블에 표시될 그룹화된 이벤트 타입
interface EventGroup {
  id: number; type: string; startTime: Date; lastTime: Date; startTimeString: string;
  duration: number; maxDb: number; level: StatusLevel; location: string;
}

// --- 2. 스타일 및 상수 ---
const statusStyles: Record<StatusLevel, StatusStyle> = {
  safe: { bg: 'bg-emerald-50 shadow-[inset_0_2px_10px_rgba(16,185,129,0.1)]', text: 'text-emerald-500', badge: 'bg-emerald-100 text-emerald-600' },
  warning: { bg: 'bg-amber-50 shadow-[inset_0_2px_10px_rgba(245,158,11,0.1)]', text: 'text-amber-500', badge: 'bg-amber-100 text-amber-600' },
  danger: { bg: 'bg-rose-50 shadow-[inset_0_2px_10px_rgba(244,63,94,0.1)]', text: 'text-rose-500', badge: 'bg-rose-100 text-rose-600' }
}
const buildingName = '동국대학교 D-Log'
const unitName = '3140호'
const CHART_MAX_LENGTH = 30; // 차트에 표시할 최대 데이터 포인트 수

// --- 3. 상태 관리 ---
const state = reactive<{
  currentStatus: StatusInfo;
  latestEvent: NoiseEvent;
  recentEvents: EventGroup[]; // 완료된 이벤트 그룹 목록
  // [추가] 중재 및 사과 메시지 상태 및 시각
  mediationSentStatus: boolean;
  mediationSentTime: string | null;
  apologySentStatus: boolean;
  apologySentTime: string | null;
}>({
  currentStatus: { level: 'safe', label: '준비', description: '관제 시스템을 초기화 중입니다.', avgDb: 0, riskScore: 0 },
  latestEvent: { id: 0, time: '-', type: '대기 중', db: 0, probability: 0, level: 'safe', location: '-', note: '연결 확인 중...', lastUpdatedAt: new Date(0) },
  recentEvents: [],
  // 초기값 설정
  mediationSentStatus: false,
  mediationSentTime: null,
  apologySentStatus: false,
  apologySentTime: null,
})

const activeEventGroup = ref<EventGroup | null>(null); // 현재 진행중인 이벤트 그룹
const now = ref(new Date()); // 지속시간 계산을 위한 실시간 시간
const isLoading = ref(false);
const error = ref<string | null>(null);
let alertAudio: HTMLAudioElement | null = null;

// 실시간 차트 전용 데이터
const liveChartLabels = ref<string[]>([]);
const liveChartData = ref<number[]>([]);

// --- 4. API 설정 ---
const CONFIG = { url: 'http://localhost:8080/get_latest_noise_data' }

// --- 5. 데이터 처리 로직 ---
const fetchMobiusData = async () => {
  isLoading.value = true;
  try {
    const res = await axios.get(CONFIG.url);
    if (res.data && Object.keys(res.data).length > 0) {
      processUpdate(res.data);
      error.value = null;
    }
  } catch (err: any) { error.value = `수신 에러: ${err.message}`; } 
  finally { isLoading.value = false; }
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

// Mobius에서 받은 데이터를 처리하는 메인 함수
const processUpdate = (data: any) => {
  const analysis = data.analysis || data;
  if (!analysis.result && typeof analysis.db_level === 'undefined') return;

  const eventTime = new Date();
  
  // 노트 메시지 생성 로직
  const notes = [];
  // [임의 필드명] 실제 백엔드 데이터 필드명으로 수정 필요!
  const isApologySent = analysis.apology_sent || data.action?.apology_sent; 
  const isMediationSent = analysis.mediation_sent || data.action?.mediation_sent;

  if (isApologySent) {
    notes.push('사과 메시지 발송됨');
    state.apologySentStatus = true;
    // [임의 필드명] 실제 백엔드 데이터 필드명으로 수정 필요!
    state.apologySentTime = analysis.apology_timestamp || eventTime.toLocaleTimeString('ko-KR', { hour12: false });
  } else {
    state.apologySentStatus = false;
    state.apologySentTime = null;
  }
  if (isMediationSent) {
    state.mediationSentStatus = true;
    // [임의 필드명] 실제 백엔드 데이터 필드명으로 수정 필요!
    state.mediationSentTime = analysis.mediation_timestamp || eventTime.toLocaleTimeString('ko-KR', { hour12: false });
  } else {
    state.mediationSentStatus = false;
    state.mediationSentTime = null;
  }

  const note = notes.length > 0 ? notes.join(', ') : '모니터링 중';

  const newEvent: NoiseEvent = {
    id: eventTime.getTime(),
    time: eventTime.toLocaleTimeString('ko-KR', { hour12: false }),
    type: analysis.result || '소음 감지',
    db: analysis.db_level ?? 0,
    probability: (analysis.probability ?? 1) * 100,
    level: severityToLevel(analysis.severity),
    location: analysis.target || data.action?.target || '측정 구역',
    note: note,
    lastUpdatedAt: eventTime,
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
      startTimeString: newEvent.time, duration: 0, maxDb: newEvent.db, level: newEvent.level, location: newEvent.location
    };
  } else if (activeEventGroup.value.type === newEvent.type) {
    activeEventGroup.value.lastTime = eventTime;
    if (newEvent.db > activeEventGroup.value.maxDb) activeEventGroup.value.maxDb = newEvent.db;
    if (levelToNumber(newEvent.level) > levelToNumber(activeEventGroup.value.level)) activeEventGroup.value.level = newEvent.level;
  } else {
    finalizeActiveGroup();
    activeEventGroup.value = {
      id: newEvent.id, type: newEvent.type, startTime: eventTime, lastTime: eventTime,
      startTimeString: newEvent.time, duration: 0, maxDb: newEvent.db, level: newEvent.level, location: newEvent.location
    };
  }
};

// --- 6. UI 렌더링을 위한 Computed 속성 ---
// 히스토리 테이블에 표시될 최종 목록 (진행중 이벤트 + 완료된 이벤트)
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

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { enabled: true } },
  scales: { 
    y: { min: 20, max: 100, grid: { color: '#F2F4F6' } }, 
    x: { 
      display: true,
      grid: { display: false },
      ticks: {
        font: { size: 9 },
        color: '#6B7280',
        maxRotation: 0,
        autoSkip: true,
        autoSkipPadding: 20,
      }
    } 
  },
  animation: false as const, // 실시간 업데이트 시에는 false로 설정
}

// 실시간 차트 업데이트 함수
const updateLiveChart = () => {
    const newLabels = [...liveChartLabels.value];
    const newData = [...liveChartData.value];
  
    const date = new Date();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    const timeString = `${hours}'${minutes}'${seconds}`;
    
    let newDbValue = Math.random() * 10 + 30; // 기본 baseline
    // 마지막으로 실제 이벤트가 수신된 지 2.1초가 지나지 않았다면 실제 db값을 사용
    if (new Date().getTime() - state.latestEvent.lastUpdatedAt.getTime() < 2100) {
      newDbValue = state.latestEvent.db;
    }

  newLabels.push(timeString);
  newData.push(newDbValue);

  if (newLabels.length > CHART_MAX_LENGTH) {
    newLabels.shift();
    newData.shift();
  }
  
  // 배열 전체를 교체하여 반응성 오류 방지
  liveChartLabels.value = newLabels;
  liveChartData.value = newData;
};


// --- 7. 리포트 추출 ---
const exportToCSV = () => {
  const headers = ['최초 감지 시각', '지속 시간(초)', '유형', '최대 강도(dB)', '상태'];
  const rows = displayEvents.value.map(e => [
    e.startTimeString,
    e.duration,
    e.type,
    e.maxDb,
    e.level
  ]);
  let csv = "\uFEFF" + headers.join(",") + "\n";
  rows.forEach(r => { csv += r.join(",") + "\n"; });
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `DLOG_Report_${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
};

const exportToPDF = async () => { 
  const element = document.getElementById('report-area');
  if (!element) return;
  isLoading.value = true;
  try {
    const canvas = await html2canvas(element, { scale: 2, useCORS: true });
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    pdf.save(`DLOG_Evidence_${new Date().toISOString().split('T')[0]}.pdf`);
  } catch (err) {
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};


// --- 8. 라이프사이클 훅 ---
let mobiusTimer: any, watchdogTimer: any, nowTimer: any, chartTimer: any;

onMounted(() => {
  // 차트 데이터 초기화
  const initialTime = new Date();
  const initialLabels: string[] = [];
  const initialData: number[] = [];
  for (let i = 0; i < CHART_MAX_LENGTH; i++) {
    const date = new Date(initialTime.getTime() - (CHART_MAX_LENGTH - 1 - i) * 2000); // 이전 시간 계산
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    initialLabels.push(`${hours}'${minutes}'${seconds}`);
    initialData.push(35); // 초기값 35로 통일
  }
  liveChartLabels.value = initialLabels;
  liveChartData.value = initialData;

  fetchMobiusData(); // 초기 데이터 로드

  // 타이머 설정
  mobiusTimer = setInterval(fetchMobiusData, 2000);
  chartTimer = setInterval(updateLiveChart, 2000);
  nowTimer = setInterval(() => now.value = new Date(), 1000);
  watchdogTimer = setInterval(() => {
    if (activeEventGroup.value && (new Date().getTime() - activeEventGroup.value.lastTime.getTime() > 5000)) {
      finalizeActiveGroup();
    }
  }, 5000);
})

onUnmounted(() => { 
  clearInterval(mobiusTimer);
  clearInterval(watchdogTimer);
  clearInterval(nowTimer);
  clearInterval(chartTimer);
})
</script>

<style>
body { font-family: 'Pretendard', sans-serif; background-color: #F9FAFB; }
/* PDF 캡처 시 버튼 등을 제외하고 싶다면 클래스로 제어 가능 */
@media print { .no-print { display: none; } }
</style>