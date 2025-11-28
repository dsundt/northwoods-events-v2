// ============================================================================
// Multi-Model Image Generation API
// Supports: Google Gemini (AI Studio + Vertex AI), OpenAI DALL-E 3
// 
// SIMPLE SETUP (just need API key):
//   - GOOGLE_GEMINI_API_KEY from https://aistudio.google.com/app/apikey
//   - Models: gemini-2.0-flash-preview-image-generation, imagen-3.0
//
// ADVANCED SETUP (for Gemini 3 Pro Image):
//   - Also add: GOOGLE_CLOUD_PROJECT_ID, GOOGLE_CLOUD_REGION
//   - Models: gemini-3.0-pro-image-generation (Vertex AI)
//
// Docs: https://ai.google.dev/gemini-api/docs/image-generation
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
      case 'gemini-3-pro':
        return await generateWithGemini3Pro(req, res, prompt);
      
      default:
        return res.status(400).json({ 
          error: `Unsupported model: ${model}`,
          supportedModels: ['dall-e-3', 'google-gemini', 'gemini-3-pro']
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
 * Generate image with Google Gemini
 * 
 * Simple setup: Just needs GOOGLE_GEMINI_API_KEY (from AI Studio)
 * Advanced setup: Add GOOGLE_CLOUD_PROJECT_ID for Vertex AI / Gemini 3 Pro
 * 
 * AI Studio: https://aistudio.google.com/app/apikey
 * Vertex AI: https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro-image
 */
async function generateWithGemini3Pro(req, res, prompt) {
  const apiKey = process.env.GOOGLE_GEMINI_API_KEY;
  const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID;
  const region = process.env.GOOGLE_CLOUD_REGION || 'us-central1';
  
  // Check for API key (minimum requirement)
  if (!apiKey) {
    return res.status(503).json({
      error: 'Google API key not configured',
      message: 'Set GOOGLE_GEMINI_API_KEY environment variable',
      setup: {
        steps: [
          '1. Go to: https://aistudio.google.com/app/apikey',
          '2. Create an API key',
          '3. Add to Vercel: vercel env add GOOGLE_GEMINI_API_KEY production',
          '4. Redeploy: vercel --prod'
        ],
        optional: 'For Gemini 3 Pro Image, also add GOOGLE_CLOUD_PROJECT_ID'
      }
    });
  }
  
  let lastError = null;
  
  // Strategy 1: Try AI Studio API first (simpler, just needs API key)
  const aiStudioModels = [
    'gemini-2.0-flash-preview-image-generation',
    'gemini-2.0-flash-exp-image-generation',
    'gemini-2.0-flash-exp'
  ];
  
  for (const model of aiStudioModels) {
    try {
      const result = await tryAIStudioModel(apiKey, model, prompt);
      if (result.success) {
        return res.status(200).json(result);
      }
      lastError = result.error || 'No image in response';
    } catch (error) {
      console.error(`AI Studio model ${model} failed:`, error.message);
      lastError = error.message;
    }
  }
  
  // Strategy 2: Try Imagen 3 via AI Studio
  try {
    const result = await tryImagen3(apiKey, prompt);
    if (result.success) {
      return res.status(200).json(result);
    }
    lastError = result.error;
  } catch (error) {
    console.error('Imagen 3 failed:', error.message);
    lastError = error.message;
  }
  
  // Strategy 3: Try Vertex AI (if project ID is configured)
  if (projectId) {
    try {
      const result = await tryVertexAIGemini3Pro(projectId, region, apiKey, prompt);
      if (result.success) {
        return res.status(200).json(result);
      }
      lastError = result.error;
    } catch (error) {
      console.error('Vertex AI failed:', error.message);
      lastError = error.message;
    }
  }
  
  // All strategies failed
  return res.status(503).json({
    error: 'Google Gemini image generation not available',
    message: 'All Gemini image generation models failed',
    details: lastError,
    troubleshooting: [
      '1. Verify API key at: https://aistudio.google.com/app/apikey',
      '2. Check if image generation models are available in your region',
      '3. Some models require billing enabled on Google Cloud project',
      '4. For Gemini 3 Pro: Add GOOGLE_CLOUD_PROJECT_ID for Vertex AI access'
    ],
    recommendation: 'Use DALL-E 3 as fallback while troubleshooting',
    configuredCredentials: {
      apiKey: !!apiKey,
      projectId: !!projectId,
      region: region
    },
    docsUrl: 'https://ai.google.dev/gemini-api/docs/image-generation'
  });
}

/**
 * Try Vertex AI endpoint with Gemini 3 Pro Image
 * 
 * Endpoint: https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/publishers/google/models/{MODEL}:generateContent
 */
async function tryVertexAIGemini3Pro(projectId, region, apiKey, prompt) {
  console.log(`Trying Vertex AI Gemini 3 Pro Image (project: ${projectId}, region: ${region})...`);
  
  // Gemini 3 Pro Image model IDs to try
  const modelIds = [
    'gemini-3.0-pro-image-generation',
    'gemini-3-pro-image',
    'gemini-3.0-pro-vision'
  ];
  
  for (const modelId of modelIds) {
    try {
      const endpoint = `https://${region}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${region}/publishers/google/models/${modelId}:generateContent`;
      
      console.log(`Trying Vertex AI model: ${modelId}`);
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
          'x-goog-user-project': projectId
        },
        body: JSON.stringify({
          contents: [{
            role: 'user',
            parts: [{
              text: `Generate a high-quality, photorealistic image: ${prompt}`
            }]
          }],
          generationConfig: {
            responseModalities: ['IMAGE', 'TEXT'],
            temperature: 0.8,
            candidateCount: 1
          },
          safetySettings: [
            { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_ONLY_HIGH' },
            { category: 'HARM_CATEGORY_HATE_SPEECH', threshold: 'BLOCK_ONLY_HIGH' },
            { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_ONLY_HIGH' },
            { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_ONLY_HIGH' }
          ]
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Vertex AI ${modelId} error:`, errorText);
        continue;
      }
      
      const data = await response.json();
      
      // Extract image from response
      if (data.candidates && data.candidates[0]?.content?.parts) {
        for (const part of data.candidates[0].content.parts) {
          if (part.inlineData && part.inlineData.data) {
            console.log(`Image generated successfully with Vertex AI ${modelId}`);
            return {
              success: true,
              imageBase64: part.inlineData.data,
              mimeType: part.inlineData.mimeType || 'image/png',
              model: `vertex-ai/${modelId}`,
              cost: 0.02,
              size: '1024x1024'
            };
          }
        }
      }
      
      // Check for safety block
      if (data.candidates?.[0]?.finishReason === 'SAFETY') {
        return {
          success: false,
          error: 'Content blocked by safety filters'
        };
      }
      
    } catch (error) {
      console.error(`Vertex AI ${modelId} exception:`, error.message);
    }
  }
  
  return { success: false, error: 'All Vertex AI models failed' };
}

/**
 * Try AI Studio (Generative Language API) with a specific model
 */
async function tryAIStudioModel(apiKey, model, prompt) {
  console.log(`Trying AI Studio model: ${model}...`);
  
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
          { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_ONLY_HIGH' },
          { category: 'HARM_CATEGORY_HATE_SPEECH', threshold: 'BLOCK_ONLY_HIGH' },
          { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_ONLY_HIGH' },
          { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_ONLY_HIGH' }
        ]
      })
    }
  );
  
  if (!response.ok) {
    const errorText = await response.text();
    console.error(`AI Studio ${model} failed:`, errorText);
    return { success: false, error: errorText };
  }
  
  const data = await response.json();
  
  // Extract image from response
  if (data.candidates && data.candidates[0]?.content?.parts) {
    for (const part of data.candidates[0].content.parts) {
      if (part.inlineData && part.inlineData.data) {
        console.log(`Image generated successfully with AI Studio ${model}`);
        return {
          success: true,
          imageBase64: part.inlineData.data,
          mimeType: part.inlineData.mimeType || 'image/png',
          model: model,
          cost: 0.02,
          size: '1024x1024'
        };
      }
    }
  }
  
  // Check for safety block
  if (data.candidates?.[0]?.finishReason === 'SAFETY') {
    return {
      success: false,
      error: 'Content blocked by safety filters'
    };
  }
  
  return { success: false, error: 'No image in response' };
}

/**
 * Try Imagen 3 via AI Studio predict endpoint
 */
async function tryImagen3(apiKey, prompt) {
  console.log('Trying Imagen 3 via AI Studio...');
  
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
    console.error('Imagen 3 failed:', errorText);
    return { success: false, error: errorText };
  }
  
  const data = await response.json();
  
  if (data.predictions && data.predictions[0]) {
    const prediction = data.predictions[0];
    const imageBase64 = prediction.bytesBase64Encoded || prediction.image || prediction.data;
    
    if (imageBase64) {
      console.log('Image generated successfully with Imagen 3');
      return {
        success: true,
        imageBase64: imageBase64,
        model: 'imagen-3.0',
        cost: 0.02,
        size: '1024x1024'
      };
    }
  }
  
  return { success: false, error: 'No image in Imagen 3 response' };
}
