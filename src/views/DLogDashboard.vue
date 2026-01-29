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
                <th class="px-8 py-4">감지 시간</th>
                <th class="px-8 py-4">유형</th>
                <th class="px-8 py-4 font-mono">강도(dB)</th>
                <th class="px-8 py-4 text-right">상태</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 text-sm text-[#333D4B]">
              <tr v-for="event in state.recentEvents" :key="event.id" class="hover:bg-gray-50/50 transition-colors">
                <td class="px-8 py-5 text-gray-400 font-medium">{{ event.time }}</td>
                <td class="px-8 py-5 font-bold">{{ event.type }}</td>
                <td class="px-8 py-5 font-mono font-bold">{{ event.db }}</td>
                <td class="px-8 py-5 text-right font-bold">
                  <span :class="statusStyles[event.level].badge" class="px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-tighter">
                    {{ event.level }}
                  </span>
                </td>
              </tr>
              <tr v-if="state.recentEvents.length === 0">
                <td colspan="4" class="px-8 py-20 text-center text-gray-400 font-medium">Mobius 데이터를 수신 중입니다...</td>
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

// --- 1. 타입 정의 (인덱싱 에러 방지) ---
type StatusLevel = 'safe' | 'warning' | 'danger'
interface StatusStyle { bg: string; text: string; badge: string; }
interface StatusInfo { level: StatusLevel; label: string; description: string; avgDb: number; riskScore: number; }
interface NoiseEvent { id: number; time: string; type: string; db: number; probability: number; level: StatusLevel; location: string; note: string; }

// --- 2. 스타일 및 상수 ---
const statusStyles: Record<StatusLevel, StatusStyle> = {
  safe: { bg: 'bg-emerald-50 shadow-[inset_0_2px_10px_rgba(16,185,129,0.1)]', text: 'text-emerald-500', badge: 'bg-emerald-100 text-emerald-600' },
  warning: { bg: 'bg-amber-50 shadow-[inset_0_2px_10px_rgba(245,158,11,0.1)]', text: 'text-amber-500', badge: 'bg-amber-100 text-amber-600' },
  danger: { bg: 'bg-rose-50 shadow-[inset_0_2px_10px_rgba(244,63,94,0.1)]', text: 'text-rose-500', badge: 'bg-rose-100 text-rose-600' }
}

const buildingName = '동국대학교 D-Log'
const unitName = '3140호'

// --- 3. 상태 관리 ---
const state = reactive<{
  currentStatus: StatusInfo;
  latestEvent: NoiseEvent;
  recentEvents: NoiseEvent[];
}>({
  currentStatus: { level: 'safe', label: '준비', description: '관제 시스템을 초기화 중입니다.', avgDb: 0, riskScore: 0 },
  latestEvent: { id: 0, time: '-', type: '대기 중', db: 0, probability: 0, level: 'safe', location: '-', note: '연결 확인 중...' },
  recentEvents: []
})

const isLoading = ref(false)
const error = ref<string | null>(null)
let alertAudio: HTMLAudioElement | null = null

// --- 4. Mobius API 설정 ---
const CONFIG = {
  // 백엔드 프록시 API를 통해 Mobius 데이터 호출
  url: 'http://localhost:8080/get_latest_noise_data'
}

// --- 5. 데이터 연동 및 처리 ---
const fetchMobiusData = async () => {
  isLoading.value = true
  try {
    // 백엔드 API 호출 시 더 이상 Mobius 전용 헤더는 필요 없음
    const res = await axios.get(CONFIG.url)
    
    // 백엔드가 이미 한번 파싱했으므로, 바로 데이터 사용
    const parsed = res.data
    if (parsed) {
      processUpdate(parsed)
      error.value = null
    }
  } catch (err: any) {
    error.value = `수신 에러: ${err.message}`
  } finally {
    isLoading.value = false
  }
}

const processUpdate = (data: any) => {
  // 0. 디버깅: 데이터가 실제로 어떻게 들어오는지 확인
  console.log("실시간 수신 데이터:", data);

  // 1. 데이터 유효성 검사 (빈 객체 {} 방지)
  if (!data || Object.keys(data).length === 0) {
    console.warn("수신된 데이터가 비어있습니다.");
    return;
  }

  /**
   * [핵심 수정] 유연한 데이터 매핑
   * data 안에 analysis가 있으면 그걸 쓰고, 없으면 data 자체를 analysis로 취급합니다.
   */
  const analysis = data.analysis ? data.analysis : data;
  
  // 만약 핵심 필드인 result(또는 db_level)가 없다면 구조가 잘못된 것
  if (!analysis.result && !analysis.db_level) {
    console.error("데이터 구조가 예상과 다릅니다. 'analysis' 또는 'result' 필드가 없습니다.", data);
    return;
  }

  // 2. severity에 따른 상태(StatusLevel) 매핑
  const sev = analysis.severity || 'Green';
  const level: StatusLevel = (sev === 'Red' || sev === 'danger') ? 'danger' : 
                             (sev === 'Yellow' || sev === 'warning') ? 'warning' : 'safe';
  
  // 3. 시간 설정
  const now = new Date().toLocaleTimeString('ko-KR', { hour12: false });

  // 4. 알림음 (Red/danger 등급 시 실행)
  if (level === 'danger') {
    if (!alertAudio) alertAudio = new Audio('/sounds/alert.wav');
    alertAudio.play().catch(() => {});
  }

  // 5. 새로운 이벤트 객체 생성 (Optional Chaining ?. 을 사용하여 에러 방지)
  const newEvent: NoiseEvent = {
    id: Date.now(),
    time: now,
    type: analysis.result || '소음 감지', 
    db: analysis.db_level ?? 0,
    probability: (analysis.probability ?? 1) * 100,
    level,
    location: analysis.target || data.action?.target || '측정 구역',
    note: (analysis.mediation_sent || data.action?.mediation_sent) ? '중재 메시지 발송됨' : '모니터링 중'
  };

  // 6. 상태 업데이트 (UI 반영)
  state.latestEvent = newEvent;
  state.currentStatus = {
    level,
    label: level === 'safe' ? '안전' : (level === 'warning' ? '주의' : '위험'),
    description: `${newEvent.type} 감지 - ${newEvent.note}`,
    avgDb: newEvent.db,
    riskScore: level === 'safe' ? 10 : (level === 'warning' ? 45 : 95)
  };
  
  // 7. 최근 이벤트 목록에 추가 (중복 방지 및 최신순 정렬)
  if (state.recentEvents.length === 0 || state.recentEvents[0].time !== now) {
    state.recentEvents = [newEvent, ...state.recentEvents].slice(0, 10);
  }
};

// --- 6. 시각화 (Chart.js) 설정 ---
const chartData = computed(() => ({
  labels: state.recentEvents.slice().reverse().map(e => e.time.split(':').slice(1).join(':')),
  datasets: [{
    label: 'dB',
    data: state.recentEvents.slice().reverse().map(e => e.db),
    borderColor: '#3182F6',
    backgroundColor: 'rgba(49, 130, 246, 0.1)',
    fill: true,
    tension: 0.4,
    pointRadius: 6,
    pointBackgroundColor: state.recentEvents.slice().reverse().map(e => 
      e.level === 'danger' ? '#F43F5E' : e.level === 'warning' ? '#F59E0B' : '#10B981'
    )
  }]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { enabled: true } },
  scales: { y: { min: 20, max: 100, grid: { color: '#F2F4F6' } }, x: { grid: { display: false } } }
}

// --- 7. 리포트 추출 (CSV & PDF) ---
const exportToCSV = () => {
  const headers = ['시간', '유형', '강도(dB)', '정확도(%)', '상태']
  const rows = state.recentEvents.map(e => [e.time, e.type, e.db, e.probability, e.level])
  let csv = "\uFEFF" + headers.join(",") + "\n"
  rows.forEach(r => { csv += r.join(",") + "\n" })
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url; a.download = `DLOG_Report_${Date.now()}.csv`; a.click()
}

const exportToPDF = async () => {
  const element = document.getElementById('report-area')
  if (!element) return
  isLoading.value = true
  try {
    const canvas = await html2canvas(element, { scale: 2, useCORS: true })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF('p', 'mm', 'a4')
    const pdfWidth = pdf.internal.pageSize.getWidth()
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width
    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight)
    pdf.save(`DLOG_Evidence_${Date.now()}.pdf`)
  } catch (err) {
    console.error(err)
  } finally {
    isLoading.value = false
  }
}

// --- 8. 라이프사이클 ---
let timer: any = null
onMounted(() => {
  fetchMobiusData()
  timer = setInterval(fetchMobiusData, 2000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style>
body { font-family: 'Pretendard', sans-serif; background-color: #F9FAFB; }
/* PDF 캡처 시 버튼 등을 제외하고 싶다면 클래스로 제어 가능 */
@media print { .no-print { display: none; } }
</style>