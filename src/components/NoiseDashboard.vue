<template>
  <div class="admin-dashboard-container">
    <header class="dashboard-header">
      <div class="title-group">
        <h1>층간소음 통합 관제 센터 <span class="live-tag">LIVE</span></h1>
        <p class="subtitle">실시간 센서 및 AI 분석 리포트 - 101호</p>
      </div>
      <div class="dashboard-controls">
        <button @click="exportToPdf" class="btn-export" :disabled="loading">
          <span v-if="!loading">📄 리포트 내보내기 (PDF)</span>
          <span v-else>처리 중...</span>
        </button>
      </div>
    </header>

    <section class="summary-section">
      <div class="summary-card status-card" :class="latestStatus.severity.toLowerCase()">
        <div class="card-icon">⚡</div>
        <div class="card-info">
          <label>현재 상태</label>
          <h3>{{ latestStatus.status }}</h3>
        </div>
      </div>
      <div class="summary-card ai-card">
        <div class="card-icon">🤖</div>
        <div class="card-info">
          <label>최근 AI 분석</label>
          <h3>{{ latestStatus.aiResult }} <small>({{ latestStatus.probability }}%)</small></h3>
        </div>
      </div>
      <div class="summary-card noise-card">
        <div class="card-icon">🔊</div>
        <div class="card-info">
          <label>최근 소음도</label>
          <h3>{{ latestStatus.db }} <small>dB</small></h3>
        </div>
      </div>
    </section>

    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-if="loading && logs.length === 0" class="loading-state">데이터를 불러오는 중입니다...</div>

    <section class="chart-section" v-if="logs.length">
      <div class="chart-container main-chart">
        <div class="chart-header"><h4>시간대별 소음 발생 빈도</h4></div>
        <EventsOverTimeChart :chartData="eventsOverTimeChartData" />
      </div>
      <div class="chart-container side-chart">
        <div class="chart-header"><h4>심각도 분포</h4></div>
        <SeverityDistributionChart :chartData="severityChartData" />
      </div>
    </section>

    <section class="table-section" v-if="logs.length">
      <div class="section-header">
        <h4>실시간 분석 로그 (최신 50건)</h4>
      </div>
      <div class="log-table-container" id="noise-log-table">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>House ID</th>
              <th>AI 분석 결과</th>
              <th>확률</th>
              <th>심각도</th>
              <th>측정 dB</th>
              <th>조치 대상</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.event_id" class="log-row">
              <td class="time-cell">{{ new Date(log.timestamp).toLocaleTimeString() }}</td>
              <td>{{ log.house_id }}</td>
              <td class="ai-cell"><strong>{{ log.analysis.result }}</strong></td>
              <td class="prob-cell">
                <div class="prob-bar-bg">
                  <div class="prob-bar" :style="{ width: (log.analysis.probability * 100) + '%' }"></div>
                </div>
                {{ (log.analysis.probability * 100).toFixed(1) }}%
              </td>
              <td>
                <span :class="['severity-badge', log.analysis.severity.toLowerCase()]">
                  {{ log.analysis.severity }}
                </span>
              </td>
              <td class="db-cell">{{ log.analysis.db_level.toFixed(1) }} <small>dB</small></td>
              <td><span class="target-tag">{{ log.action.target }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script>
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import SeverityDistributionChart from './SeverityDistributionChart';
import EventsOverTimeChart from './EventsOverTimeChart';

export default {
  name: 'NoiseDashboard',
  components: {
    SeverityDistributionChart,
    EventsOverTimeChart
  },
  data() {
    return {
      logs: [],
      loading: false,
      error: null,
      ws: null,
    };
  },
  computed: {
    // 1. 심각도 분포 데이터
    severityChartData() {
      const severityCounts = { Red: 0, Yellow: 0, Green: 0 };
      this.logs.forEach(log => {
        if (log.analysis && log.analysis.severity) {
          severityCounts[log.analysis.severity]++;
        }
      });
      return {
        labels: Object.keys(severityCounts),
        datasets: [{
          backgroundColor: ['#e74c3c', '#f1c40f', '#2ecc71'],
          data: Object.values(severityCounts)
        }]
      };
    },
    // 2. 시간대별 빈도 데이터
    eventsOverTimeChartData() {
      const eventsByHour = {};
      this.logs.forEach(log => {
        if (log.timestamp) {
          const date = new Date(log.timestamp);
          const label = `${date.toLocaleDateString()} ${date.getHours()}:00`;
          eventsByHour[label] = (eventsByHour[label] || 0) + 1;
        }
      });
      const sortedLabels = Object.keys(eventsByHour).sort((a, b) => new Date(a) - new Date(b));
      return {
        labels: sortedLabels,
        datasets: [{
          label: '이벤트 수',
          backgroundColor: '#3498db',
          borderColor: '#3498db',
          data: sortedLabels.map(label => eventsByHour[label]),
          fill: false
        }]
      };
    },
    // 3. 최신 요약 정보 (통합 완료)
    latestStatus() {
      if (!this.logs || this.logs.length === 0) {
        return { status: '연결 중', severity: 'green', aiResult: '-', probability: 0, db: 0 };
      }
      const latest = this.logs[0];
      const statusMap = { 'Green': '정상', 'Yellow': '주의', 'Red': '위험' };
      return {
        status: statusMap[latest.analysis.severity] || '분석 중',
        severity: latest.analysis.severity || 'Green',
        aiResult: latest.analysis.result || '-',
        probability: (latest.analysis.probability * 100).toFixed(1),
        db: latest.analysis.db_level.toFixed(1)
      };
    }
  },
  methods: {
    async fetchLogs() {
      this.loading = true;
      try {
        const response = await fetch('http://localhost:8080/logs?limit=50');
        const data = await response.json();
        if (data.status === 'success') this.logs = data.logs;
      } catch (e) {
        this.error = '데이터 로드 실패: ' + e.message;
      } finally {
        this.loading = false;
      }
    },
    connectWebSocket() {
      this.ws = new WebSocket('ws://localhost:8080/ws/logs');
      this.ws.onopen = () => { this.fetchLogs(); };
      this.ws.onmessage = (event) => {
        const newLog = JSON.parse(event.data);
        this.logs.unshift(newLog);
        this.logs = this.logs.slice(0, 50);
      };
      this.ws.onclose = () => { setTimeout(() => this.connectWebSocket(), 3000); };
    },
    async exportToPdf() {
      this.loading = true;
      const element = document.getElementById('noise-log-table');
      try {
        const canvas = await html2canvas(element, { scale: 2 });
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF('p', 'mm', 'a4');
        pdf.addImage(imgData, 'PNG', 0, 0, 210, (canvas.height * 210) / canvas.width);
        pdf.save('층간소음_분석리포트.pdf');
      } catch (e) {
        alert('PDF 생성 실패: ' + e.message);
      } finally {
        this.loading = false;
      }
    }
  },
  mounted() { this.connectWebSocket(); },
  beforeDestroy() { if (this.ws) this.ws.close(); }
};
</script>

<style scoped>
.admin-dashboard-container {
  background-color: #f4f7f6;
  min-height: 100vh;
  padding: 40px;
  font-family: 'Pretendard', sans-serif;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 40px;
}

.live-tag {
  background: #ff4757;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.7rem;
  animation: blink 1s infinite;
}

.summary-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 25px;
  margin-bottom: 40px;
}

.summary-card {
  background: white;
  padding: 25px;
  border-radius: 15px;
  display: flex;
  align-items: center;
  box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
  border-left: 6px solid #ddd;
}
.summary-card.green { border-left-color: #2ecc71; }
.summary-card.yellow { border-left-color: #f1c40f; }
.summary-card.red { border-left-color: #e74c3c; }

.chart-section {
  display: flex;
  gap: 25px;
  margin-bottom: 40px;
}
.chart-container {
  background: white;
  padding: 25px;
  border-radius: 15px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}
.main-chart { flex: 2; }
.side-chart { flex: 1; }

.prob-bar-bg { background: #edf2f7; height: 8px; border-radius: 4px; overflow: hidden; }
.prob-bar { background: #3498db; height: 100%; transition: width 0.5s ease; }

.severity-badge {
  padding: 5px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: bold;
}
.severity-badge.green { background: #def7ec; color: #03543f; }
.severity-badge.yellow { background: #fdf6b2; color: #723b13; }
.severity-badge.red { background: #fde8e8; color: #9b1c1c; }

@keyframes blink { 50% { opacity: 0; } }
</style>