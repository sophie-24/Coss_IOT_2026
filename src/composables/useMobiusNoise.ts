import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

// 1. Mobius 데이터 구조 정의
export interface MobiusConPayload {
  analysis: {
    severity: 'Green' | 'Yellow' | 'Red'
    noiseType?: string
    db?: number
    location?: string
    [key: string]: any
  }
}

interface MobiusOptions {
  origin: string
  apiKey: string
  pollMs?: number
}

export default function useMobiusNoise(opts: MobiusOptions) {
  const MOBIUS_URL = 'https://onem2m.iotcoss.ac.kr/Mobius/ae_Namsan/cnt_noise/la'
  const pollMs = opts.pollMs ?? 2000

  // 반응형 상태 변수
  const lastCon = ref<MobiusConPayload | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  let timer: ReturnType<typeof setInterval> | null = null
  let alertAudio: HTMLAudioElement | null = null

  // 2. 알림음 재생 로직 (브라우저 정책 고려)
  const initAudio = () => {
    if (!alertAudio) {
      // public/sounds/alert.wav 경로에 파일이 있어야 합니다.
      alertAudio = new Audio('/sounds/alert.wav')
    }
  }

  const playAlert = () => {
    initAudio()
    alertAudio?.play().catch((err) => {
      // 사용자가 페이지와 상호작용(클릭 등) 하기 전에는 자동 재생이 차단될 수 있습니다.
      console.warn('오디오 재생 차단됨:', err.message)
    })
  }

  // 3. API 요청 로직
  const fetchLatestData = async () => {
    try {
      isLoading.value = true
      const response = await axios.get(MOBIUS_URL, {
        headers: {
          'X-M2M-Origin': opts.origin,
          'X-API-KEY': opts.apiKey,
          'Accept': 'application/json'
        }
      })

      // oneM2M 규격에 따른 데이터 추출
      const cin = response.data?.['m2m:cin']
      const conStr = cin?.con

      if (typeof conStr === 'string') {
        const parsed = JSON.parse(conStr) as MobiusConPayload
        lastCon.value = parsed

        // severity가 Red일 경우 알림음 발생
        if (parsed.analysis?.severity === 'Red') {
          playAlert()
        }
      }
      error.value = null
    } catch (e: any) {
      error.value = e.message || '데이터를 불러오는 중 오류가 발생했습니다.'
      console.error('[Mobius Polling Error]:', e)
    } finally {
      isLoading.value = false
    }
  }

  // 4. 생명주기 관리
  onMounted(() => {
    fetchLatestData() // 즉시 1회 실행
    timer = setInterval(fetchLatestData, pollMs) // 2초마다 실행
  })

  onUnmounted(() => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  })

  return {
    lastCon,
    isLoading,
    error,
    refresh: fetchLatestData
  }
}