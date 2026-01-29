<template>
  <div class="dashboard-container">
    <div class="dashboard-header">
      <h1 class="main-title">101호 실시간 대시보드</h1>
    </div>

    <div class="main-grid">
      <!-- Left Column -->
      <div class="column-left">
        <div class="card status-card" :class="statusClass">
          <h2 class="card-title">실시간 상태</h2>
          <div class="realtime-status-content">
            <div class="status-indicator-ring">
              <div class="status-indicator-dot"></div>
            </div>
            <p class="status-text">{{ currentStatusText }}</p>
          </div>
          <div class="subtle-divider"></div>
          <div class="noise-cause">
            <h3 class="cause-title">탐지된 소음 원인</h3>
            <p class="cause-text">{{ noiseCause }}</p>
          </div>
        </div>

        <div class="card event-log-card">
          <h2 class="card-title">최근 주요 알림</h2>
          <ul class="event-list">
            <li v-if="eventLog.length === 0" class="no-events">최근 알림이 없습니다.</li>
            <li v-for="(event, index) in eventLog" :key="index" class="event-item" :class="`is-${event.severity.toLowerCase()}`">
              <div class="event-details">
                <div class="event-header">
                  <span class="event-severity-icon">{{ event.severity === 'Danger' ? 'R' : 'Y' }}</span>
                  <span class="event-time">{{ event.timestamp }}</span>
                  <span class="event-cause">{{ event.cause }}</span>
                </div>
                <div class="event-meta">
                  <span class="event-duration">{{ event.duration.toFixed(1) }}s</span>
                  <div class="event-confirmation" :class="{ 'is-confirmed': event.confirmed }">
                    <span class="confirmation-icon">✓</span>
                    <span>{{ event.confirmed ? '확인' : '미확인' }}</span>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <!-- Right Column -->
      <div class="column-right">
        <div class="summary-grid">
          <div class="card count-card">
            <h2 class="card-title">누적 경고 (Red)</h2>
            <p class="metric-value">{{ cumulativeRed }}</p>
          </div>
          <div class="card count-card">
            <h2 class="card-title">누적 주의 (Yellow)</h2>
            <p class="metric-value">{{ cumulativeYellow }}</p>
          </div>
        </div>

        <div class="card chart-card">
          <h2 class="card-title">월간 시간대별 소음 누적 (최근 1개월)</h2>
          <div class="chart-container">
            <div class="bar-chart">
              <div v-for="(value, key) in monthlyData" :key="key" class="bar-item">
                <div class="bar" :style="{ height: value + '%' }"></div>
                <span class="bar-label">{{ key }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card chart-card" v-if="vibration_spectrum && vibration_spectrum.length > 0">
          <h2 class="card-title">실시간 진동 주파수 분석</h2>
          <div class="chart-container">
            <div class="bar-chart">
              <div v-for="(item, index) in vibration_spectrum" :key="index" class="bar-item">
                <div class="bar" :style="{ height: item.magnitude_percent + '%' }" :title="`~${item.magnitude.toFixed(2)}`"></div>
                <span class="bar-label">{{ item.frequency_range }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card report-card">
          <h2 class="card-title">주간 리포트 생성</h2>
          <div class="report-controls">
            <div class="date-picker">
              <label for="start-date">시작일</label>
              <input type="date" id="start-date" v-model="report_start_date">
            </div>
            <div class="date-picker">
              <label for="end-date">종료일</label>
              <input type="date" id="end-date" v-model="report_end_date">
            </div>
            <button @click="downloadReport" class="report-button">리포트 생성 및 다운로드</button>
          </div>
        </div>
      </div>
    </div>
    
  </div>
</template>

<script>
export default {
  name: 'Dashboard',
  data() {
    return {
      backendHttpUrl: 'http://localhost:8080',
      backendWsUrl: 'ws://localhost:8080',
      currentStatus: 'Normal',
      noiseCause: '데이터 수신 대기 중...',
      eventLog: [],
      cumulativeRed: 0,
      cumulativeYellow: 0,
      monthlyData: { '오전': 0, '오후': 0, '저녁': 0, '심야': 0 },
      vibration_spectrum: [],
      report_start_date: '',
      report_end_date: '',
    };
  },
  computed: {
    statusClass() {
      return {
        'is-normal': this.currentStatus === 'Normal',
        'is-warning': this.currentStatus === 'Warning',
        'is-danger': this.currentStatus === 'Danger',
      };
    },
    currentStatusText() {
       const statusMap = { 'Normal': '정상', 'Warning': '주의', 'Danger': '경고' };
       return statusMap[this.currentStatus] || '알 수 없음';
    }
  },
  methods: {
    processInitialLogs(logs) {
      let redCount = 0;
      let yellowCount = 0;
      const monthly = { '오전': 0, '오후': 0, '저녁': 0, '심야': 0 };
      const recentEvents = [];

      logs.forEach(log => {
        const severity = log && log.analysis && log.analysis.severity;
        if (severity === 'Red') redCount++;
        if (severity === 'Yellow') yellowCount++;

        if (severity === 'Red' || severity === 'Yellow') {
            recentEvents.push({
                severity: severity === 'Red' ? 'Danger' : 'Warning',
                timestamp: log.timestamp ? new Date(log.timestamp).toLocaleTimeString('ko-KR') : 'N/A',
                cause: (log && log.analysis && log.analysis.result) || '알 수 없음',
                confirmed: Math.random() > 0.5,
                duration: (log && log.analysis && log.analysis.duration) || 0,
            });
        }
        
        if (log && log.timestamp) {
          const logDate = new Date(log.timestamp);
          if (!isNaN(logDate)) {
            const hour = logDate.getHours();
            if (hour >= 6 && hour < 12) monthly['오전']++;
            else if (hour >= 12 && hour < 18) monthly['오후']++;
            else if (hour >= 18 && hour < 24) monthly['저녁']++;
            else monthly['심야']++;
          }
        }
      });

      this.cumulativeRed = redCount;
      this.cumulativeYellow = yellowCount;
      this.eventLog = recentEvents.slice(0, 7).reverse(); // Show oldest first
      
      const maxCount = Math.max(...Object.values(monthly));
      if (maxCount > 0) {
        for (const key in monthly) {
          this.monthlyData[key] = (monthly[key] / maxCount) * 100;
        }
      }
    },
    async fetchInitialData() {
      try {
        const response = await fetch(`${this.backendHttpUrl}/logs`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        if (data.status === 'success' && data.logs) {
          this.processInitialLogs(data.logs);
        }
      } catch (error) {
        console.error("Could not fetch initial data:", error);
        this.noiseCause = "백엔드 연결 실패";
      }
    },
    connectWebSocket() {
      const ws = new WebSocket(`${this.backendWsUrl}/ws/logs`);

      ws.onopen = () => { this.noiseCause = "실시간 데이터 수신 중..."; };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const severity = data.analysis && data.analysis.severity;
        const duration = data.analysis && data.analysis.duration;
        
        // This is a final decision from server, so we use it directly
        if (severity === 'Red' || severity === 'Yellow') {
          this.currentStatus = severity === 'Red' ? 'Danger' : 'Warning';
          this.noiseCause = (data.analysis && data.analysis.result) || '알 수 없음';
          
          this.eventLog.unshift({
            severity: this.currentStatus,
            timestamp: new Date(data.timestamp).toLocaleTimeString('ko-KR'),
            cause: this.noiseCause,
            confirmed: Math.random() > 0.4, // Simulate confirmation
            duration: duration || 0.0,
          });
          if (this.eventLog.length > 7) this.eventLog.pop();

          if (this.currentStatus === 'Danger') this.cumulativeRed++;
          if (this.currentStatus === 'Warning') this.cumulativeYellow++;
        }
        // NOTE: The 'currentStatus' will only be reset to 'Normal' by the stateful server logic,
        // which sends a 'Green' event. We can add specific handling for Green if needed,
        // but for now the server only sends final decisions on loud events.
      };

      ws.onclose = () => {
        this.noiseCause = "연결이 끊겼습니다. 재연결 중...";
        setTimeout(this.connectWebSocket, 5000);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        ws.close();
      };
    },
    downloadReport() {
      if (!this.report_start_date || !this.report_end_date) {
        alert("리포트를 생성할 시작일과 종료일을 모두 선택해주세요.");
        return;
      }
      const house_id = '101호'; // Hardcoded for this dashboard
      const url = `${this.backendHttpUrl}/report/pdf?house_id=${house_id}&start_date=${this.report_start_date}&end_date=${this.report_end_date}`;
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${house_id}_${this.report_start_date}_to_${this.report_end_date}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  },
  mounted() {
    this.fetchInitialData();
    this.connectWebSocket();
    
    // Set default dates for the report
    const today = new Date();
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(today.getDate() - 7);
    this.report_end_date = today.toISOString().slice(0, 10);
    this.report_start_date = sevenDaysAgo.toISOString().slice(0, 10);
  }
};
</script>

<style scoped>
:root {
  --font-family-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --color-background: #F8F9FA;
  --color-normal: #28a745;
  --color-warning: #ffc107;
  --color-danger: #dc3545;
  --color-text-primary: #212529;
  --color-text-secondary: #6c757d;
  --color-card-background: #FFFFFF;
  --color-divider: #E9ECEF;
  --shadow-color: rgba(0, 0, 0, 0.04);
}

.dashboard-container { background-color: var(--color-background); font-family: var(--font-family-sans); min-height: 100vh; padding: 1.5rem; color: var(--color-text-primary); }
.main-title { font-size: 1.75rem; font-weight: 600; margin-bottom: 1.5rem; }
.main-grid { display: grid; grid-template-columns: 1fr; gap: 1.5rem; }
@media (min-width: 1024px) { .main-grid { grid-template-columns: 1fr 1fr; } }
.column-left, .column-right { display: flex; flex-direction: column; gap: 1.5rem; }
.card { background-color: var(--color-card-background); border-radius: 12px; padding: 1.25rem; border: 1px solid var(--color-divider); box-shadow: 0 2px 8px var(--shadow-color); }
.card-title { font-size: 0.9rem; font-weight: 600; color: var(--color-text-secondary); margin-bottom: 1rem; }

.status-card { text-align: center; }
.realtime-status-content { display: flex; align-items: center; justify-content: center; gap: 1.5rem; margin: 0.5rem 0 1.5rem; }
.status-indicator-ring { width: 70px; height: 70px; border-radius: 50%; display: flex; justify-content: center; align-items: center; transition: background-color 0.4s ease; }
.status-indicator-dot { width: 45px; height: 45px; border-radius: 50%; transition: background-color 0.4s ease; }
.status-text { font-size: 1.75rem; font-weight: 600; transition: color 0.4s ease; }

.is-normal .status-indicator-ring { background-color: rgba(40, 167, 69, 0.1); }
.is-normal .status-indicator-dot { background-color: var(--color-normal); }
.is-normal .status-text { color: var(--color-normal); }
.is-warning .status-indicator-ring { background-color: rgba(255, 193, 7, 0.15); }
.is-warning .status-indicator-dot { background-color: var(--color-warning); }
.is-warning .status-text { color: var(--color-warning); }
.is-danger .status-indicator-ring { background-color: rgba(220, 53, 69, 0.1); }
.is-danger .status-indicator-dot { background-color: var(--color-danger); }
.is-danger .status-text { color: var(--color-danger); }

.subtle-divider { height: 1px; background-color: var(--color-divider); margin: 0; }
.noise-cause { padding-top: 1.25rem; }
.cause-title { font-size: 0.8rem; color: var(--color-text-secondary); margin-bottom: 0.25rem; }
.cause-text { font-size: 1.1rem; font-weight: 500; }

.event-log-card .event-list { list-style: none; padding: 0; margin: 0; max-height: 220px; overflow-y: auto; }
.no-events { color: var(--color-text-secondary); font-size: 0.9rem; }
.event-item { padding: 0.75rem 0.25rem; border-bottom: 1px solid var(--color-divider); }
.event-item:last-child { border-bottom: none; }
.event-details { display: flex; justify-content: space-between; align-items: center; }
.event-header { display: flex; align-items: center; gap: 0.75rem; }
.event-severity-icon { flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; color: white; }
.is-danger .event-severity-icon { background-color: var(--color-danger); }
.is-warning .event-severity-icon { background-color: var(--color-warning); }
.event-time { font-size: 0.9rem; font-family: monospace; color: var(--color-text-primary); }
.event-cause { font-size: 0.9rem; color: var(--color-text-secondary); }

.event-meta { display: flex; align-items: center; gap: 0.75rem; }
.event-duration { font-size: 0.9rem; font-family: monospace; color: var(--color-text-secondary); }
.event-confirmation { display: flex; align-items: center; font-size: 0.8rem; padding: 0.25rem 0.5rem; border-radius: 6px; color: var(--color-text-secondary); background-color: #f1f3f5; }
.event-confirmation.is-confirmed { color: var(--color-normal); background-color: rgba(40, 167, 69, 0.1); }
.confirmation-icon { font-weight: bold; margin-right: 0.25rem; opacity: 0; }
.event-confirmation.is-confirmed .confirmation-icon { opacity: 1; }

.summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.count-card { text-align: center; }
.metric-value { font-size: 2.5rem; font-weight: 700; color: var(--color-text-primary); }

.chart-card { flex-grow: 1; }
.chart-container { height: 150px; }
.bar-chart { display: flex; height: 100%; justify-content: space-around; align-items: flex-end; gap: 1rem; }
.bar-item { display: flex; flex-direction: column; align-items: center; flex-grow: 1; }
.bar { width: 80%; background-color: var(--color-text-secondary); border-radius: 4px 4px 0 0; transition: height 0.5s ease; animation: bar-grow 0.5s ease-out; }
.bar-label { font-size: 0.75rem; color: var(--color-text-secondary); margin-top: 0.5rem; }

.report-card .report-controls { display: flex; flex-direction: column; gap: 1rem; }
.report-card .date-picker { display: flex; flex-direction: column; gap: 0.25rem; }
.report-card label { font-size: 0.8rem; color: var(--color-text-secondary); }
.report-card input[type="date"] {
  padding: 0.5rem;
  border: 1px solid var(--color-divider);
  border-radius: 6px;
  font-family: var(--font-family-sans);
}
.report-button {
  background-color: var(--color-text-primary);
  color: white;
  border: none;
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease;
}
.report-button:hover { background-color: #000; }

@keyframes bar-grow { from { height: 0; } }
</style>
