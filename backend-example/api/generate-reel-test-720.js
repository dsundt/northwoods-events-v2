// TEST VERSION - Using 720:1280 ratio
// Copy of generate-reel.js with 720:1280 for testing

const fetch = require('node-fetch');

exports.config = {
  maxDuration: 300,
};

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept');
  res.setHeader('Access-Control-Max-Age', '86400');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  if (req.method === 'GET') {
    return res.status(200).json({
      status: 'ok',
      testVersion: '720:1280',
      message: 'This endpoint uses 720:1280 aspect ratio for testing'
    });
  }
  
  const { prompt } = req.body;
  const RUNWAY_API_KEY = process.env.RUNWAY_API_KEY;
  
  if (!RUNWAY_API_KEY || !prompt) {
    return res.status(400).json({ error: 'Missing API key or prompt' });
  }
  
  try {
    // Test with 720:1280
    const genResponse = await fetch('https://api.dev.runwayml.com/v1/text_to_video', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RUNWAY_API_KEY}`,
        'Content-Type': 'application/json',
        'X-Runway-Version': '2024-11-06',
      },
      body: JSON.stringify({
        promptText: prompt,
        duration: 8,
        ratio: '720:1280', // TESTING 720:1280
        model: 'veo3.1_fast',
      }),
    });
    
    if (!genResponse.ok) {
      const errorText = await genResponse.text();
      throw new Error(`Runway API error: ${errorText}`);
    }
    
    const genData = await genResponse.json();
    
    return res.status(200).json({
      success: true,
      taskId: genData.id,
      testedRatio: '720:1280',
      message: 'Task created with 720:1280 ratio - poll for completion',
    });
    
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
};
