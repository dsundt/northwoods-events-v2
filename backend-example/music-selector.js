/**
 * Music Selector for Pre-Downloaded Track Library
 * 
 * Use this if you have a subscription to Epidemic Sound, Artlist, or
 * have downloaded tracks from YouTube Audio Library.
 * 
 * Setup:
 * 1. Download 10-20 tracks covering different moods
 * 2. Place in /backend-example/music/ folder
 * 3. Update musicLibrary object below with your filenames
 * 4. Uncomment music selection code in generate-reel.js
 */

const path = require('path');

/**
 * Music library organized by mood
 * Update these arrays with your downloaded track filenames
 */
const musicLibrary = {
  // Upbeat, energetic tracks for festivals, parties, celebrations
  upbeat: [
    'upbeat-outdoor-adventure.mp3',
    'upbeat-summer-festival.mp3',
    'upbeat-celebration.mp3',
  ],
  
  // Calm, ambient tracks for art, galleries, peaceful events
  calm: [
    'calm-ambient-peaceful.mp3',
    'calm-piano-reflection.mp3',
  ],
  
  // Energetic, motivational tracks for sports, races, competitions
  energetic: [
    'energetic-rock-sport.mp3',
    'energetic-electronic-action.mp3',
  ],
  
  // Acoustic, folk tracks for food, wine, dining events
  acoustic: [
    'acoustic-folk-gathering.mp3',
    'acoustic-guitar-pleasant.mp3',
  ],
  
  // Electronic, modern tracks for music festivals, nightlife
  electronic: [
    'electronic-dance-festival.mp3',
    'electronic-house-party.mp3',
  ],
  
  // Nature, outdoor tracks for hiking, camping, outdoor events
  nature: [
    'nature-adventure-outdoor.mp3',
    'nature-peaceful-forest.mp3',
  ],
  
  // Winter, holiday tracks for winter events
  winter: [
    'winter-acoustic-cozy.mp3',
    'winter-upbeat-holiday.mp3',
  ],
  
  // Family-friendly, playful tracks for family events
  family: [
    'family-happy-playful.mp3',
    'family-cheerful-fun.mp3',
  ],
};

/**
 * Determine appropriate music mood based on event details
 * @param {string} eventTitle - Event title
 * @param {string} eventLocation - Event location (optional)
 * @param {string} eventDate - Event date (optional)
 * @returns {string} Mood category
 */
function determineMood(eventTitle, eventLocation = '', eventDate = '') {
  const text = `${eventTitle} ${eventLocation}`.toLowerCase();
  
  // Check for specific keywords
  if (text.match(/art|gallery|museum|exhibit|sculpture|painting/)) {
    return 'calm';
  }
  
  if (text.match(/sport|race|marathon|run|bike|compete|championship|game/)) {
    return 'energetic';
  }
  
  if (text.match(/music|concert|festival|band|dj|performance|show/)) {
    return 'electronic';
  }
  
  if (text.match(/food|wine|dining|taste|culinary|chef|restaurant/)) {
    return 'acoustic';
  }
  
  if (text.match(/hike|camp|trail|outdoor|adventure|kayak|canoe/)) {
    return 'nature';
  }
  
  if (text.match(/family|kids|children|youth|school/)) {
    return 'family';
  }
  
  // Check for winter/holiday events by keywords or date
  if (text.match(/winter|snow|ski|ice|holiday|christmas/) || isWinterMonth(eventDate)) {
    return 'winter';
  }
  
  // Default to upbeat
  return 'upbeat';
}

/**
 * Check if date is in winter months (Nov-Feb)
 */
function isWinterMonth(dateStr) {
  if (!dateStr) return false;
  
  try {
    const date = new Date(dateStr);
    const month = date.getMonth(); // 0-11
    return month >= 10 || month <= 1; // Nov, Dec, Jan, Feb
  } catch (e) {
    return false;
  }
}

/**
 * Select a random music track from the library
 * @param {Object} event - Event object with title, location, start_utc
 * @returns {string} Absolute path to music file
 */
function selectMusic(event) {
  const mood = determineMood(
    event.title || '',
    event.location || '',
    event.start_utc || ''
  );
  
  console.log(`Event: "${event.title}" → Mood: ${mood}`);
  
  const tracks = musicLibrary[mood];
  
  if (!tracks || tracks.length === 0) {
    console.warn(`No tracks found for mood: ${mood}, using upbeat`);
    return selectRandomTrack(musicLibrary.upbeat);
  }
  
  return selectRandomTrack(tracks);
}

/**
 * Select random track from array
 */
function selectRandomTrack(tracks) {
  const randomIndex = Math.floor(Math.random() * tracks.length);
  const filename = tracks[randomIndex];
  const fullPath = path.join(__dirname, 'music', filename);
  
  console.log(`Selected track: ${filename}`);
  
  return fullPath;
}

/**
 * Get all available moods
 */
function getAvailableMoods() {
  return Object.keys(musicLibrary);
}

/**
 * Get track count for a mood
 */
function getTrackCount(mood) {
  return musicLibrary[mood] ? musicLibrary[mood].length : 0;
}

/**
 * Validate that music files exist
 */
function validateMusicLibrary() {
  const fs = require('fs');
  const errors = [];
  
  for (const [mood, tracks] of Object.entries(musicLibrary)) {
    for (const track of tracks) {
      const fullPath = path.join(__dirname, 'music', track);
      if (!fs.existsSync(fullPath)) {
        errors.push(`Missing: ${track} (mood: ${mood})`);
      }
    }
  }
  
  return errors;
}

module.exports = {
  selectMusic,
  determineMood,
  getAvailableMoods,
  getTrackCount,
  validateMusicLibrary,
};

/**
 * Example usage:
 * 
 * const { selectMusic } = require('./music-selector');
 * 
 * const event = {
 *   title: "Minocqua Music Festival",
 *   location: "Minocqua, WI",
 *   start_utc: "2025-07-15T18:00:00Z"
 * };
 * 
 * const musicPath = selectMusic(event);
 * // Returns: /path/to/backend-example/music/electronic-dance-festival.mp3
 */
