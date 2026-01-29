<script>
import { Line } from 'vue-chartjs';

export default {
  name: 'EventsOverTimeChart',
  extends: Line,
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
          display: false
        },
        title: {
          display: true,
          text: 'Noise Events Over Time'
        },
        scales: {
          xAxes: [{
            scaleLabel: {
              display: true,
              labelString: 'Time'
            }
          }],
          yAxes: [{
            scaleLabel: {
              display: true,
              labelString: 'Number of Events'
            },
            ticks: {
                beginAtZero: true,
                stepSize: 1
            }
          }]
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