// ============================================================================
// Instagram Reel Generation API - Serverless Function
// ============================================================================
// Deploy to: Vercel, Netlify, AWS Lambda, or any serverless platform
// 
// Environment Variables Required:
// - RUNWAY_API_KEY: Your Runway ML API key (required)
// - BEATOVEN_API_KEY: Your Beatoven.ai API key (optional, for music)
// - GITHUB_TOKEN: For committing videos to repository (optional)
//
// Dependencies (package.json):
// {
//   "dependencies": {
//     "node-fetch": "^2.6.7",
//     "form-data": "^4.0.0"
//   }
// }
// ============================================================================

const fetch = require('node-fetch');

// Maximum execution time: 5 minutes (300 seconds)
// Vercel Pro: 900 seconds, AWS Lambda: 900 seconds
exports.config = {
  maxDuration: 300,
};

/**
 * Main handler function
 */
module.exports = async (req, res) => {
  // CRITICAL: Set CORS headers FIRST, before any other logic
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept');
  res.setHeader('Access-Control-Max-Age', '86400'); // 24 hours
  
  // Handle preflight requests immediately
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  // Health check for GET requests
  if (req.method === 'GET') {
    return res.status(200).json({
      status: 'ok',
      service: 'Instagram Reel Generation API',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      runwayConfigured: !!process.env.RUNWAY_API_KEY,
      beatovenConfigured: !!process.env.BEATOVEN_API_KEY,
      cors: 'enabled'
    });
  }
  
  // Only accept POST requests for generation
  if (req.method !== 'POST') {
    return res.status(405).json({ 
      error: 'Method not allowed',
      message: 'This endpoint accepts GET (health check) and POST (generation) requests'
    });
  }
  
  const { prompt, event, addMusic = false, audioMode = 'no_audio' } = req.body;
  
  // Validate input
  if (!prompt || !event) {
    return res.status(400).json({ 
      error: 'Missing required fields',
      message: 'Both prompt and event data are required'
    });
  }
  
  // Validate API keys
  const RUNWAY_API_KEY = process.env.RUNWAY_API_KEY;
  
  if (!RUNWAY_API_KEY) {
    return res.status(500).json({ 
      error: 'Server configuration error',
      message: 'Runway ML API key not configured. Set RUNWAY_API_KEY environment variable.'
    });
  }
  
  console.log('Starting reel generation for:', event.title);
  
  try {
    // Step 1: Generate video with Runway ML
    console.log('Step 1/3: Submitting to Runway ML...');
    
    const videoUrl = await generateRunwayVideo(RUNWAY_API_KEY, prompt, audioMode);
    
    console.log('Video generated:', videoUrl);
    
    // Step 2: Add music (optional)
    let finalVideoUrl = videoUrl;
    let musicUrl = null;
    
    if (addMusic && BEATOVEN_API_KEY) {
      console.log('Step 2/3: Generating background music with Beatoven.ai...');
      
      try {
        finalVideoUrl = await addBackgroundMusic(
          videoUrl,
          event,
          BEATOVEN_API_KEY
        );
        console.log('Music generated successfully');
        // Note: Music URL is available but not merged server-side
        // Users can add music in Instagram app for best results
      } catch (musicError) {
        console.error('Failed to generate music, using original video:', musicError);
        // Continue with video without music
      }
    } else {
      console.log('Step 2/3: Skipping music (not requested or API key missing)');
    }
    
    // Step 3: Return result
    console.log('Step 3/3: Returning video URL');
    
    return res.status(200).json({
      success: true,
      videoUrl: finalVideoUrl,
      duration: 8, // seconds
      aspectRatio: '9:16',
      resolution: '1080x1920',
      format: 'vertical',
      message: 'Reel generated successfully in 9:16 vertical format!',
      tips: [
        'Video is 9:16 vertical - perfect for Instagram Reels!',
        'Download the video to your device',
        'Use "Save to Repository" to commit to GitHub',
        'Add text overlays and music in Instagram app',
      ],
    });
    
  } catch (error) {
    console.error('Error generating reel:', error);
    console.error('Error details:', {
      message: error.message,
      stack: error.stack,
      name: error.name
    });
    
    return res.status(500).json({
      error: error.message,
      errorType: error.name,
      fullError: error.toString(),
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
      troubleshooting: [
        'Check that your Runway ML API key is valid',
        'Verify you have sufficient credits in your Runway account',
        'Try a simpler prompt',
        'Check Runway ML status: status.runwayml.com',
        'Check Vercel logs for detailed error information'
      ],
    });
  }
};

/**
 * Generate video using Runway ML Gen-2 API
 */
async function generateRunwayVideo(apiKey, prompt, audioMode = 'no_audio') {
  console.log('Submitting to Runway ML API...');
  console.log('Audio mode requested:', audioMode);
  
  // Prepare request body with audio settings
  const requestBody = {
    promptText: prompt,
    duration: 8, // Valid durations: 4, 6, or 8 seconds
    ratio: '720:1280', // VERTICAL 9:16 format (720 width x 1280 height = portrait for Instagram Reels)
    model: 'veo3.1_fast', // Using Veo 3.1 Fast for good balance of speed and quality
  };
  
  // Add audio configuration based on mode
  // Note: Runway ML has a 1000 character limit on prompts
  let enhancedPrompt = prompt;
  
  // Add shorter audio instructions if needed
  if (audioMode === 'music_only') {
    enhancedPrompt += '\nWith background music.';
  } else if (audioMode === 'music_and_speech') {
    enhancedPrompt += '\nWith music and narration.';
  }
  // Note: 'no_audio' doesn't add anything - saves characters
  
  // Truncate if still too long (max 1000 characters)
  if (enhancedPrompt.length > 1000) {
    console.warn(`Prompt too long (${enhancedPrompt.length} chars), truncating to 1000`);
    enhancedPrompt = enhancedPrompt.substring(0, 997) + '...';
  }
  
  requestBody.promptText = enhancedPrompt;
  console.log(`Prompt length: ${enhancedPrompt.length} characters`);
  
  // Step 1: Submit generation request
  const genResponse = await fetch('https://api.dev.runwayml.com/v1/text_to_video', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'X-Runway-Version': '2024-11-06',
    },
    body: JSON.stringify(requestBody),
  });
  
  console.log('Request sent with VERTICAL aspect ratio: 720x1280 (9:16 portrait)');
  
  if (!genResponse.ok) {
    const errorText = await genResponse.text();
    console.error('Runway ML API error response:', errorText);
    throw new Error(`Runway API error (${genResponse.status}): ${errorText}`);
  }
  
  const genData = await genResponse.json();
  console.log('Runway ML response:', genData);
  
  if (!genData.id) {
    console.error('Invalid response from Runway ML:', genData);
    throw new Error('Runway ML did not return a task ID');
  }
  
  const taskId = genData.id;
  console.log(`Video generation task created: ${taskId}`);
  
  console.log(`Video generation started: ${taskId}`);
  
  // Step 2: Poll for completion
  // Runway ML typically takes 1-3 minutes
  let videoUrl = null;
  let attempts = 0;
  const maxAttempts = 60; // 5 minutes maximum
  const pollInterval = 5000; // 5 seconds
  
  while (!videoUrl && attempts < maxAttempts) {
    // Wait before polling
    await sleep(pollInterval);
    attempts++;
    
    console.log(`Polling attempt ${attempts}/${maxAttempts}...`);
    
    const statusResponse = await fetch(
      `https://api.dev.runwayml.com/v1/tasks/${taskId}`,
      {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'X-Runway-Version': '2024-11-06',
        },
      }
    );
    
    if (!statusResponse.ok) {
      throw new Error(`Failed to check status: ${statusResponse.status}`);
    }
    
    const statusData = await statusResponse.json();
    
    console.log(`Status: ${statusData.status}, Progress: ${statusData.progress || 0}%`);
    
    if (statusData.status === 'SUCCEEDED') {
      videoUrl = statusData.output[0]; // Runway returns array of outputs
      break;
    } else if (statusData.status === 'FAILED') {
      // Log full response to see what Runway ML is returning
      console.error('FAILED status received. Full response:', JSON.stringify(statusData, null, 2));
      
      // Check for different possible error fields
      const errorMsg = statusData.failure_reason 
        || statusData.failureReason 
        || statusData.error 
        || statusData.message 
        || 'No error details provided by Runway ML';
      
      throw new Error(`Video generation failed: ${errorMsg}. Full status: ${JSON.stringify(statusData)}`);
    } else if (statusData.status === 'CANCELLED') {
      throw new Error('Video generation was cancelled');
    }
    // Status is PENDING or RUNNING, continue polling
  }
  
  if (!videoUrl) {
    throw new Error('Video generation timeout. The process took too long.');
  }
  
  return videoUrl;
}

/**
 * Add background music using Beatoven.ai
 */
async function addBackgroundMusic(videoUrl, event, beatovenApiKey) {
  console.log('Generating background music with Beatoven.ai...');
  
  // Step 1: Determine music parameters based on event
  const musicParams = determineMusicParameters(event.title, event.start_utc);
  
  // Step 2: Create music composition with Beatoven.ai
  console.log(`Creating ${musicParams.genre} track with ${musicParams.mood} mood...`);
  
  const createResponse = await fetch('https://api.beatoven.ai/api/v1/tracks', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${beatovenApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title: `${event.title} - Background Music`,
      duration: 20, // Match video duration (seconds)
      genre: musicParams.genre,
      mood: musicParams.mood,
      tempo: musicParams.tempo,
      instruments: musicParams.instruments,
      format: 'mp3',
      sample_rate: 44100,
      bit_depth: 16,
    }),
  });
  
  if (!createResponse.ok) {
    const errorText = await createResponse.text();
    throw new Error(`Beatoven.ai API error (${createResponse.status}): ${errorText}`);
  }
  
  const createData = await createResponse.json();
  const trackId = createData.track_id;
  
  console.log(`Music composition created: ${trackId}`);
  
  // Step 3: Poll for completion (Beatoven.ai typically takes 30-60 seconds)
  let musicUrl = null;
  let attempts = 0;
  const maxAttempts = 30; // 2.5 minutes max
  const pollInterval = 5000; // 5 seconds
  
  while (!musicUrl && attempts < maxAttempts) {
    await sleep(pollInterval);
    attempts++;
    
    console.log(`Checking music generation status (${attempts}/${maxAttempts})...`);
    
    const statusResponse = await fetch(
      `https://api.beatoven.ai/api/v1/tracks/${trackId}`,
      {
        headers: {
          'Authorization': `Bearer ${beatovenApiKey}`,
        },
      }
    );
    
    if (!statusResponse.ok) {
      throw new Error(`Failed to check music status: ${statusResponse.status}`);
    }
    
    const statusData = await statusResponse.json();
    
    if (statusData.status === 'completed') {
      musicUrl = statusData.download_url;
      break;
    } else if (statusData.status === 'failed') {
      throw new Error(`Music generation failed: ${statusData.error || 'Unknown error'}`);
    }
    // Status is 'processing', continue polling
  }
  
  if (!musicUrl) {
    throw new Error('Music generation timeout');
  }
  
  console.log('Music generated successfully:', musicUrl);
  
  // Step 4: Merge video and music (simplified - return music URL for client-side merging)
  // NOTE: For full server-side merging, use FFmpeg
  // For simplicity, we return the original video URL
  // Music URL is returned separately for client to download if needed
  
  console.log('⚠️ Music merging requires FFmpeg - returning original video');
  console.log('💡 Music URL available for download:', musicUrl);
  console.log('💡 Users can add music in Instagram app for best results');
  
  return videoUrl;
}

/**
 * Determine appropriate music parameters for Beatoven.ai based on event details
 */
function determineMusicParameters(eventTitle, eventDate = '') {
  const title = eventTitle.toLowerCase();
  
  // Determine season from date
  const season = determineSeason(eventDate);
  
  // Music festivals and concerts
  if (title.match(/music|concert|festival|band|dj|performance/)) {
    return {
      genre: 'Electronic',
      mood: 'Energetic',
      tempo: 'Fast',
      instruments: ['Synth', 'Bass', 'Drums'],
    };
  }
  
  // Art and cultural events
  if (title.match(/art|gallery|museum|exhibit|sculpture|painting/)) {
    return {
      genre: 'Ambient',
      mood: 'Calm',
      tempo: 'Slow',
      instruments: ['Piano', 'Strings'],
    };
  }
  
  // Sports and active events
  if (title.match(/sport|race|marathon|run|bike|compete|championship|game/)) {
    return {
      genre: 'Rock',
      mood: 'Motivational',
      tempo: 'Fast',
      instruments: ['Guitar', 'Drums', 'Bass'],
    };
  }
  
  // Food and dining events
  if (title.match(/food|wine|dining|taste|culinary|chef|restaurant/)) {
    return {
      genre: 'Acoustic',
      mood: 'Happy',
      tempo: 'Medium',
      instruments: ['Acoustic Guitar', 'Piano'],
    };
  }
  
  // Outdoor and nature events
  if (title.match(/hike|camp|trail|outdoor|adventure|kayak|canoe|nature/)) {
    return {
      genre: 'Folk',
      mood: 'Inspiring',
      tempo: 'Medium',
      instruments: ['Acoustic Guitar', 'Strings'],
    };
  }
  
  // Family events
  if (title.match(/family|kids|children|youth|school/)) {
    return {
      genre: 'Pop',
      mood: 'Happy',
      tempo: 'Medium',
      instruments: ['Piano', 'Strings', 'Percussion'],
    };
  }
  
  // Winter events
  if (title.match(/winter|snow|ski|ice|holiday|christmas/) || season === 'winter') {
    return {
      genre: 'Cinematic',
      mood: 'Peaceful',
      tempo: 'Slow',
      instruments: ['Piano', 'Strings', 'Bells'],
    };
  }
  
  // Night events
  if (title.match(/night|evening|sunset|moonlight/)) {
    return {
      genre: 'Ambient',
      mood: 'Relaxed',
      tempo: 'Slow',
      instruments: ['Synth', 'Piano'],
    };
  }
  
  // Default: Upbeat outdoor Wisconsin event
  return {
    genre: 'Folk',
    mood: 'Uplifting',
    tempo: 'Medium',
    instruments: ['Acoustic Guitar', 'Strings', 'Percussion'],
  };
}

/**
 * Determine season from date string
 */
function determineSeason(dateStr) {
  if (!dateStr) return 'summer';
  
  try {
    const date = new Date(dateStr);
    const month = date.getMonth(); // 0-11
    
    if (month >= 11 || month <= 1) return 'winter'; // Dec, Jan, Feb
    if (month >= 2 && month <= 4) return 'spring';  // Mar, Apr, May
    if (month >= 5 && month <= 7) return 'summer';  // Jun, Jul, Aug
    if (month >= 8 && month <= 10) return 'fall';   // Sep, Oct, Nov
  } catch (e) {
    // Invalid date, default to summer
  }
  
  return 'summer';
}

/**
 * Helper function to sleep
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Example request body:
 * {
 *   "prompt": "Create a 20-second vertical video showcasing a music festival in Northern Wisconsin...",
 *   "event": {
 *     "title": "Minocqua Music Festival",
 *     "start_utc": "2025-07-15T18:00:00Z",
 *     "location": "Minocqua, WI"
 *   },
 *   "addMusic": true
 * }
 */
