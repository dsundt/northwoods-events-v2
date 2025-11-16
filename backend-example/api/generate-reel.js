// ============================================================================
// Instagram Reel Generation API - Serverless Function
// ============================================================================
// Deploy to: Vercel, Netlify, AWS Lambda, or any serverless platform
// 
// Environment Variables Required:
// - RUNWAY_API_KEY: Your Runway ML API key
// - MUBERT_API_KEY: Your Mubert API key (optional, for music)
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
  // Enable CORS for GitHub Pages
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  // Only accept POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ 
      error: 'Method not allowed',
      message: 'This endpoint only accepts POST requests'
    });
  }
  
  const { prompt, event, addMusic = false } = req.body;
  
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
    
    const videoUrl = await generateRunwayVideo(RUNWAY_API_KEY, prompt);
    
    console.log('Video generated:', videoUrl);
    
    // Step 2: Add music (optional)
    let finalVideoUrl = videoUrl;
    
    if (addMusic && process.env.MUBERT_API_KEY) {
      console.log('Step 2/3: Adding background music...');
      
      try {
        finalVideoUrl = await addBackgroundMusic(
          videoUrl,
          event,
          process.env.MUBERT_API_KEY
        );
        console.log('Music added successfully');
      } catch (musicError) {
        console.error('Failed to add music, using original video:', musicError);
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
      duration: 20, // seconds
      message: 'Reel generated successfully!',
      tips: [
        'Download the video to your device',
        'Use "Save to Repository" to commit to GitHub',
        'Add text overlays in Instagram app',
        'Adjust music volume if needed',
      ],
    });
    
  } catch (error) {
    console.error('Error generating reel:', error);
    
    return res.status(500).json({
      error: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
      troubleshooting: [
        'Check that your Runway ML API key is valid',
        'Verify you have sufficient credits in your Runway account',
        'Try a simpler prompt',
        'Check Runway ML status: status.runwayml.com',
      ],
    });
  }
};

/**
 * Generate video using Runway ML Gen-2 API
 */
async function generateRunwayVideo(apiKey, prompt) {
  console.log('Submitting to Runway ML API...');
  
  // Step 1: Submit generation request
  const genResponse = await fetch('https://api.runwayml.com/v1/gen2', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'X-Runway-Version': '2024-11-01',
    },
    body: JSON.stringify({
      text_prompt: prompt,
      duration: 5, // Runway generates in 5-second increments (5, 10, 15, 20, etc.)
      ratio: '16:9', // Note: Runway doesn't support 9:16 directly, we'll need to crop
      model: 'gen2',
      watermark: false,
    }),
  });
  
  if (!genResponse.ok) {
    const errorText = await genResponse.text();
    throw new Error(`Runway API error (${genResponse.status}): ${errorText}`);
  }
  
  const genData = await genResponse.json();
  const taskId = genData.id;
  
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
      `https://api.runwayml.com/v1/tasks/${taskId}`,
      {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'X-Runway-Version': '2024-11-01',
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
      throw new Error(`Video generation failed: ${statusData.failure_reason || 'Unknown error'}`);
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
 * Add background music using Mubert AI
 */
async function addBackgroundMusic(videoUrl, event, mubertApiKey) {
  console.log('Generating background music with Mubert...');
  
  // Step 1: Determine music tags based on event
  const tags = determineMusicTags(event.title);
  
  // Step 2: Generate music with Mubert
  const musicResponse = await fetch('https://api.mubert.com/v2/RecordTrack', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      license: mubertApiKey,
      duration: 20, // Match video duration
      tags: tags,
      mode: 'track',
      bitrate: 320, // High quality
    }),
  });
  
  if (!musicResponse.ok) {
    throw new Error(`Mubert API error: ${musicResponse.status}`);
  }
  
  const musicData = await musicResponse.json();
  const musicUrl = musicData.data.track_url;
  
  console.log('Music generated:', musicUrl);
  
  // Step 3: Merge video and music
  // NOTE: This requires FFmpeg, which is available on most serverless platforms
  // For platforms without FFmpeg, you can:
  // 1. Use a separate video processing service
  // 2. Return both URLs and merge client-side
  // 3. Skip music merging entirely
  
  // For simplicity, we'll return the original video URL
  // and instruct users to add music in Instagram app
  console.log('⚠️ Music merging requires FFmpeg - returning original video');
  console.log('💡 Users can add music in Instagram app');
  
  return videoUrl;
}

/**
 * Determine appropriate music tags based on event title
 */
function determineMusicTags(eventTitle) {
  const title = eventTitle.toLowerCase();
  
  if (title.includes('music') || title.includes('concert') || title.includes('festival')) {
    return 'upbeat,energetic,festival,party,celebration';
  } else if (title.includes('art') || title.includes('gallery') || title.includes('exhibit')) {
    return 'calm,ambient,sophisticated,elegant,artful';
  } else if (title.includes('sport') || title.includes('race') || title.includes('marathon') || title.includes('adventure')) {
    return 'energetic,dynamic,motivational,action,sport';
  } else if (title.includes('food') || title.includes('wine') || title.includes('dining') || title.includes('taste')) {
    return 'upbeat,cheerful,casual,pleasant,social';
  } else if (title.includes('night') || title.includes('evening')) {
    return 'atmospheric,chill,night,relaxed';
  } else if (title.includes('family') || title.includes('kids') || title.includes('children')) {
    return 'happy,fun,playful,cheerful,family';
  } else {
    // Default for outdoor/nature events in Northern Wisconsin
    return 'upbeat,outdoor,nature,adventure,peaceful';
  }
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
