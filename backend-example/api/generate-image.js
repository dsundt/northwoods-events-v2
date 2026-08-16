// ============================================================================
// Image Generation API - OpenAI DALL-E 3
// ============================================================================

const fetch = require('node-fetch');

module.exports = async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    const { prompt, eventData } = req.body;
    
    if (!prompt) {
      return res.status(400).json({ error: 'Prompt is required' });
    }
    
    console.log(`Generating image with DALL-E 3`);
    console.log(`Prompt: ${prompt.substring(0, 100)}...`);
    
    return await generateWithDALLE3(req, res, prompt);
    
  } catch (error) {
    console.error('Image generation error:', error);
    return res.status(500).json({
      error: error.message,
      details: error.toString()
    });
  }
};

/**
 * Generate image with OpenAI DALL-E 3
 */
async function generateWithDALLE3(req, res, prompt) {
  const apiKey = process.env.OPENAI_API_KEY;
  
  if (!apiKey) {
    return res.status(503).json({
      error: 'OpenAI API key not configured',
      message: 'Please set OPENAI_API_KEY environment variable',
      setup: [
        '1. Get API key from: https://platform.openai.com/api-keys',
        '2. Add to Vercel: vercel env add OPENAI_API_KEY production',
        '3. Redeploy: vercel --prod'
      ]
    });
  }
  
  try {
    const response = await fetch('https://api.openai.com/v1/images/generations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'dall-e-3',
        prompt: prompt,
        n: 1,
        size: '1024x1024',
        quality: 'standard',
        response_format: 'b64_json'
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'DALL-E API error');
    }
    
    const data = await response.json();
    
    return res.status(200).json({
      success: true,
      imageBase64: data.data[0].b64_json,
      model: 'dall-e-3',
      cost: 0.04,
      size: '1024x1024'
    });
    
  } catch (error) {
    console.error('DALL-E error:', error);
    return res.status(500).json({
      error: error.message,
      model: 'dall-e-3'
    });
  }
}
