export default async function handler(req) {
  if (req.method !== "POST") return new Response("Not allowed", {status:405});
  try {
    const { prompt } = await req.json();
    const res = await fetch("https://api.deepseek.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${process.env.DEEPSEEK_KEY}`
      },
      body: JSON.stringify({
        model: "deepseek-chat",
        messages: [{role: "user", content: prompt}],
        temperature: 0.7
      })
    });
    const data = await res.json();
    return new Response(JSON.stringify(data), {headers: {"Content-Type":"application/json"}});
  } catch (err) {
    return new Response("Error", {status:500});
  }
}
