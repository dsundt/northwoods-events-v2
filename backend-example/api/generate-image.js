// ============================================================================
// Multi-Model Image Generation API
// Supports: OpenAI DALL-E 3, Google Gemini/Imagen
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
    const { prompt, model = 'dall-e-3', eventData } = req.body;
    
    if (!prompt) {
      return res.status(400).json({ error: 'Prompt is required' });
    }
    
    console.log(`Generating image with model: ${model}`);
    console.log(`Prompt: ${prompt.substring(0, 100)}...`);
    
    // Route to appropriate model
    switch (model) {
      case 'dall-e-3':
        return await generateWithDALLE3(req, res, prompt);
      
      case 'google-gemini':
      case 'google-imagen':
        return await generateWithGemini(req, res, prompt);
      
      default:
        return res.status(400).json({ 
          error: `Unsupported model: ${model}`,
          supportedModels: ['dall-e-3', 'google-gemini']
        });
    }
    
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
      message: 'Please set OPENAI_API_KEY environment variable'
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

/**
 * Generate image with Google Gemini 2.5 Flash (Imagen)
 */
async function generateWithGemini(req, res, prompt) {
  const apiKey = process.env.GOOGLE_GEMINI_API_KEY;
  
  if (!apiKey) {
    return res.status(503).json({
      error: 'Google Gemini API key not configured',
      message: 'Please set GOOGLE_GEMINI_API_KEY environment variable'
    });
  }
  
  try {
    // Use Gemini API with Imagen 3 for image generation
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${apiKey}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [{
          parts: [{
            text: `Generate an image: ${prompt}`
          }]
        }],
        generationConfig: {
          temperature: 0.8,
          topP: 0.95,
          maxOutputTokens: 8192,
        }
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Gemini API error:', errorText);
      throw new Error(`Gemini API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Check if image was generated
    // Note: Gemini API response format may vary - adjust based on actual response
    if (data.candidates && data.candidates[0]?.content?.parts) {
      const imagePart = data.candidates[0].content.parts.find(part => part.inlineData);
      
      if (imagePart && imagePart.inlineData) {
        return res.status(200).json({
          success: true,
          imageBase64: imagePart.inlineData.data,
          model: 'google-gemini-2.5-flash',
          cost: 0.02,
          size: '1024x1024'
        });
      }
    }
    
    // If image not in response, try alternative: Use Vertex AI Imagen instead
    return await generateWithVertexImagen(req, res, prompt, apiKey);
    
  } catch (error) {
    console.error('Google Gemini error:', error);
    
    // Fallback: Try Imagen via Vertex AI
    try {
      return await generateWithVertexImagen(req, res, prompt, process.env.GOOGLE_GEMINI_API_KEY);
    } catch (fallbackError) {
      return res.status(500).json({
        error: error.message,
        model: 'google-gemini',
        note: 'Gemini image generation may require different API access'
      });
    }
  }
}

/**
 * Fallback: Use Vertex AI Imagen 3 directly
 */
async function generateWithVertexImagen(req, res, prompt, apiKey) {
  // This requires Vertex AI setup with proper authentication
  // For now, return helpful error with setup instructions
  
  return res.status(503).json({
    error: 'Google image generation requires additional setup',
    message: 'Please set up Vertex AI Imagen or use Gemini API with image generation enabled',
    model: 'google-imagen',
    setupInstructions: [
      '1. Go to https://console.cloud.google.com',
      '2. Enable Vertex AI API',
      '3. Enable Imagen API',
      '4. Create service account with Vertex AI permissions',
      '5. Add credentials to Vercel environment',
      'OR',
      '1. Use Google AI Studio: https://aistudio.google.com',
      '2. Get Gemini API key with image generation',
      '3. Add GOOGLE_GEMINI_API_KEY to Vercel'
    ]
  });
}
