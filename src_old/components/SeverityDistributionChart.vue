<script>
import { Pie } from 'vue-chartjs';

export default {
  name: 'SeverityDistributionChart',
  extends: Pie,
  props: {
    chartData: {
      type: Object,
      required: true,
      default: () => ({})
    },
    chartOptions: {
      type: Object,
      default: () => ({
        responsive: true,
        maintainAspectRatio: false,
        legend: {
          display: true
        },
        title: {
          display: true,
          text: 'Severity Distribution'
        }
      })
    }
  },
  watch: {
    chartData () {
      this.renderChart(this.chartData, this.chartOptions);
    }
  },
  mounted () {
    this.renderChart(this.chartData, this.chartOptions);
  }
};
</script>