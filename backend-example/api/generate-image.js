// ============================================================================
// Multi-Model Image Generation API
// Supports: OpenAI DALL-E 3, Google Gemini 2.0 Flash (native image generation)
// 
// Gemini models tried (in order):
//   1. gemini-2.0-flash-preview-image-generation
//   2. gemini-2.0-flash-exp-image-generation
//   3. gemini-2.0-flash-exp
//   4. imagen-3.0-generate-002 (fallback)
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
 * Generate image with Google Gemini 2.0 Flash (native image generation)
 * 
 * Uses the gemini-2.0-flash-preview-image-generation model which supports
 * native image generation via the AI Studio API.
 * 
 * API Docs: https://ai.google.dev/gemini-api/docs/image-generation
 */
async function generateWithGemini(req, res, prompt) {
  const apiKey = process.env.GOOGLE_GEMINI_API_KEY;
  
  if (!apiKey) {
    return res.status(503).json({
      error: 'Google Gemini API key not configured',
      message: 'Get API key from: https://aistudio.google.com/app/apikey',
      setupSteps: [
        '1. Go to Google AI Studio: https://aistudio.google.com/app/apikey',
        '2. Click "Create API Key"',
        '3. Select or create a Google Cloud project',
        '4. Copy the API key',
        '5. Add to Vercel: vercel env add GOOGLE_GEMINI_API_KEY production',
        '6. Redeploy: vercel --prod'
      ]
    });
  }
  
  // List of models to try in order of preference
  const modelsToTry = [
    'gemini-2.0-flash-preview-image-generation',
    'gemini-2.0-flash-exp-image-generation', 
    'gemini-2.0-flash-exp'
  ];
  
  let lastError = null;
  
  for (const model of modelsToTry) {
    try {
      console.log(`Trying Google Gemini image generation with model: ${model}...`);
      
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            contents: [{
              parts: [{
                text: `Generate a high-quality image: ${prompt}`
              }]
            }],
            generationConfig: {
              responseModalities: ['IMAGE', 'TEXT'],
              responseMimeType: 'text/plain'
            },
            safetySettings: [
              {
                category: 'HARM_CATEGORY_HARASSMENT',
                threshold: 'BLOCK_ONLY_HIGH'
              },
              {
                category: 'HARM_CATEGORY_HATE_SPEECH', 
                threshold: 'BLOCK_ONLY_HIGH'
              },
              {
                category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                threshold: 'BLOCK_ONLY_HIGH'
              },
              {
                category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
                threshold: 'BLOCK_ONLY_HIGH'
              }
            ]
          })
        }
      );
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Model ${model} failed:`, errorText);
        lastError = errorText;
        continue; // Try next model
      }
      
      const data = await response.json();
      console.log(`Gemini ${model} response received`);
      
      // Extract image from response - look for inlineData in parts
      if (data.candidates && data.candidates[0]?.content?.parts) {
        for (const part of data.candidates[0].content.parts) {
          if (part.inlineData && part.inlineData.data) {
            console.log(`Image generated successfully with ${model}`);
            return res.status(200).json({
              success: true,
              imageBase64: part.inlineData.data,
              mimeType: part.inlineData.mimeType || 'image/png',
              model: model,
              cost: 0.02,
              size: '1024x1024'
            });
          }
        }
      }
      
      // Check for blocked content
      if (data.candidates && data.candidates[0]?.finishReason === 'SAFETY') {
        console.log('Content blocked by safety filters');
        return res.status(400).json({
          error: 'Content blocked by safety filters',
          message: 'The prompt was flagged by Google\'s safety filters. Try a different prompt.',
          model: model
        });
      }
      
      console.log(`No image found in response from ${model}, trying next...`);
      lastError = 'No image data in response';
      
    } catch (error) {
      console.error(`Error with model ${model}:`, error.message);
      lastError = error.message;
      continue; // Try next model
    }
  }
  
  // All models failed - try the Imagen 3 endpoint as last resort
  return await tryImagen3Endpoint(apiKey, prompt, res, lastError);
}

/**
 * Try Imagen 3 via AI Studio API (last resort fallback)
 * Note: Imagen 3 standalone may require Vertex AI for full functionality
 */
async function tryImagen3Endpoint(apiKey, prompt, res, previousError) {
  try {
    console.log('Trying Imagen 3 endpoint as fallback...');
    
    // Try the Imagen 3 generate endpoint
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key=${apiKey}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          instances: [{
            prompt: prompt
          }],
          parameters: {
            sampleCount: 1,
            aspectRatio: '1:1',
            personGeneration: 'ALLOW_ADULT'
          }
        })
      }
    );
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Imagen 3 endpoint failed:', errorText);
      throw new Error(`Imagen 3 endpoint failed: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Extract image from Imagen response
    if (data.predictions && data.predictions[0]) {
      const prediction = data.predictions[0];
      let imageBase64 = prediction.bytesBase64Encoded || prediction.image || prediction.data;
      
      if (imageBase64) {
        return res.status(200).json({
          success: true,
          imageBase64: imageBase64,
          model: 'imagen-3.0',
          cost: 0.02,
          size: '1024x1024'
        });
      }
    }
    
    throw new Error('No image data in Imagen response');
    
  } catch (imagenError) {
    console.error('Imagen 3 endpoint also failed:', imagenError);
    
    // Return comprehensive error with troubleshooting info
    return res.status(503).json({
      error: 'Google Gemini image generation not available',
      message: 'All Gemini image generation models failed',
      details: previousError || imagenError.message,
      troubleshooting: [
        '1. Verify your API key is valid at: https://aistudio.google.com/app/apikey',
        '2. Ensure the Generative Language API is enabled in Google Cloud Console',
        '3. Check if image generation is available in your region',
        '4. The API key must be from a project with billing enabled for some models',
        '5. Try waiting a few minutes and retry - the service may be temporarily unavailable'
      ],
      recommendation: 'Use DALL-E 3 instead while Gemini image generation is being set up',
      apiKeyConfigured: true,
      modelsAttempted: [
        'gemini-2.0-flash-preview-image-generation',
        'gemini-2.0-flash-exp-image-generation',
        'gemini-2.0-flash-exp',
        'imagen-3.0-generate-002'
      ],
      docsUrl: 'https://ai.google.dev/gemini-api/docs/image-generation'
    });
  }
}
