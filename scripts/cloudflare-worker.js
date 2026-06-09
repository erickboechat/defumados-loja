// Cloudflare Worker — Monitor Webhook → WhatsApp (Twilio)
//
// Deploy:
//   1. Cloudflare Dashboard → Workers & Pages → Create Worker
//   2. Cole este código
//   3. Vá em Settings → Variables:
//      - TWILIO_ACCOUNT_SID
//      - TWILIO_AUTH_TOKEN
//      - TWILIO_WHATSAPP_FROM
//      - ADMIN_WHATSAPP
//      - WEBHOOK_SECRET (opcional, para segurança)
//   4. Deploy
//   5. No Pulsetic: Alert Contacts → Webhook → URL do Worker
//      URL: https://seu-worker.workers.dev/?token=SEU_WEBHOOK_SECRET

export default {
  async fetch(request, env) {
    if (request.method === 'GET') {
      return new Response('Monitor Defumados AC — Worker ativo', { status: 200 })
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 })
    }

    const url = new URL(request.url)
    const token = url.searchParams.get('token')

    if (env.WEBHOOK_SECRET && token !== env.WEBHOOK_SECRET) {
      return new Response('Unauthorized', { status: 401 })
    }

    try {
      const body = await request.json()
      const alertType = (body.alert_type || body.alertType || '').toLowerCase()
      const monitorName = body.monitor?.name || body.monitor_name || 'defumadosac.com.br'
      const monitorUrl = body.monitor?.url || body.monitor_url || 'https://defumadosac.com.br'

      const now = new Date()
      const horaBRT = now.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })

      let subject, message

      if (alertType.includes('down')) {
        subject = '🔴 defumadosac.com.br FORA DO AR'
        message = `🔴 ALERTA: O site está FORA DO AR!\n\nData/Hora: ${horaBRT}\nMonitor: ${monitorName}\nURL: ${monitorUrl}\n\nAcesse o servidor via SSH para investigar.`
      } else if (alertType.includes('up')) {
        subject = '🟢 defumadosac.com.br VOLTOU AO AR'
        message = `🟢 O site está ONLINE novamente!\n\nData/Hora: ${horaBRT}\nMonitor: ${monitorName}\nURL: ${monitorUrl}`
      } else {
        return new Response('Unknown alert type', { status: 200 })
      }

      await sendWhatsApp(env, message)
      return new Response('OK', { status: 200 })
    } catch (e) {
      return new Response(`Error: ${e.message}`, { status: 500 })
    }
  },
}

async function sendWhatsApp(env, body) {
  const credentials = btoa(`${env.TWILIO_ACCOUNT_SID}:${env.TWILIO_AUTH_TOKEN}`)
  const formData = new URLSearchParams({
    From: `whatsapp:${env.TWILIO_WHATSAPP_FROM}`,
    To: `whatsapp:${env.ADMIN_WHATSAPP}`,
    Body: body,
  })

  const resp = await fetch(
    `https://api.twilio.com/2010-04-01/Accounts/${env.TWILIO_ACCOUNT_SID}/Messages.json`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${credentials}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    }
  )

  const result = await resp.json()
  if (!resp.ok) {
    throw new Error(`Twilio error: ${result.message || resp.status}`)
  }
}
