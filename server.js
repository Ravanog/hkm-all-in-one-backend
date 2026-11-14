const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const { spawn } = require('child_process');

const app = express();
app.use(cors());
app.use(express.json());

const MONGO_URI = process.env.MONGO_URI || 'mongodb+srv://anikush8310_db_user:nPoB0GWMD34X7aeR@cluster0.yvanywe.mongodb.net';
const BOT_TOKEN = process.env.BOT_TOKEN;
const UPDATE_CHANNEL_ID = process.env.UPDATE_CHANNEL_ID;
const LOG_CHANNEL_ID = process.env.LOG_CHANNEL_ID;
const FRONTEND_URL = (process.env.FRONTEND_URL || 'https://hkm-all-in-one-backend-q2yk.vercel.app').replace(/\/$/, '');
const TMDB_API_KEY = process.env.TMDB_API_KEY || '6abcb6bb99fb77f33c37016a28866ed2';

mongoose.connect(MONGO_URI)
  .then(() => console.log('HKM Database Connected'))
  .catch(err => console.error('MongoDB Error:', err));

const db = mongoose.connection;

const episodeSchema = new mongoose.Schema({
  season: { type: Number, default: 1 },
  episode: { type: Number, required: true },
  title: { type: String, default: '' },
  streamUrl: { type: String, required: true },
  downloadUrl: { type: String, required: true }
});

const movieSchema = new mongoose.Schema({
  title: { type: String, required: true },
  posterUrl: { type: String, default: 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=600' },
  category: { type: String, default: 'Action' },
  language: { type: String, default: 'Multi Audio' },
  rating: { type: String, default: 'N/A' },
  quality: { type: String, default: '1080p' },
  credit: { type: String, default: 'Hari_Moviez' },
  isPremium: { type: Boolean, default: false },
  views: { type: Number, default: 0 },
  streamUrl: { type: String, default: '' },
  downloadUrl: { type: String, default: '' },
  episodes: [episodeSchema],
  createdAt: { type: Date, default: Date.now }
});
const Movie = mongoose.model('Movie', movieSchema);

async function resolvePoster(title, category, providedPoster) {
  if (providedPoster && providedPoster.trim().startsWith('http')) {
    return providedPoster.trim();
  }
  if (TMDB_API_KEY) {
    try {
      const type = ['series', 'anime'].includes((category || '').toLowerCase()) ? 'tv' : 'movie';
      const resp = await fetch(`https://api.themoviedb.org/3/search/${type}?api_key=${TMDB_API_KEY}&query=${encodeURIComponent(title)}`);
      const data = await resp.json();
      if (data.results && data.results[0] && data.results[0].poster_path) {
        return `https://image.tmdb.org/t/p/w500${data.results[0].poster_path}`;
      }
    } catch (e) {}
  }
  return 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=600';
}

async function postToUpdateChannel(movieDoc, episodeInfo = null) {
  if (!BOT_TOKEN || !UPDATE_CHANNEL_ID) return;

  const directLink = `${FRONTEND_URL}/?watch=${movieDoc._id}`;
  const isEpisodic = episodeInfo !== null;
  const headerText = isEpisodic
    ? `🆕 <b>RECENTLY ADDED ${movieDoc.category.toUpperCase()} EPISODE</b>`
    : `🎬 <b>RECENTLY ADDED ${movieDoc.category.toUpperCase()}</b>`;

  const episodeLine = isEpisodic
    ? `» <b>Episode:</b> Season ${episodeInfo.season} • Episode ${episodeInfo.episode}\n`
    : '';

  const accessBadge = movieDoc.isPremium ? '👑 VIP Premium' : '🆓 Free Access';

  const caption =
    `${headerText}\n\n` +
    `» <b>Title:</b> ${movieDoc.title}\n` +
    `${episodeLine}` +
    `» <b>Rating:</b> ⭐ ${movieDoc.rating || 'N/A'}/10\n` +
    `» <b>Language:</b> 🌐 ${movieDoc.language || 'Multi Audio'}\n` +
    `» <b>Quality:</b> 🎞️ ${movieDoc.quality || '1080p'}\n` +
    `» <b>Uploaded By:</b> 💎 <b>${movieDoc.credit || 'Hari_Moviez'}</b>\n` +
    `» <b>Access:</b> ${accessBadge}\n\n` +
    `» <b>Watch / Download Link:</b>\n${directLink}`;

  const payload = {
    chat_id: UPDATE_CHANNEL_ID,
    photo: movieDoc.posterUrl,
    caption: caption,
    parse_mode: 'HTML',
    reply_markup: {
      inline_keyboard: [
        [{ text: '▶️ Watch & Download Now', url: directLink }]
      ]
    }
  };

  try {
    const tgRes = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const tgData = await tgRes.json();
    if (!tgData.ok) {
      await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: UPDATE_CHANNEL_ID, text: caption, parse_mode: 'HTML', reply_markup: payload.reply_markup })
      });
    }
  } catch (err) {
    console.error('Update Broadcast Error:', err.message);
  }
}

// Root health check endpoint for Koyeb (Fixes SIGTERM crashes)
app.get('/', (req, res) => {
  res.status(200).send('HKM Backend is active and running!');
});

app.get('/api/movies', async (req, res) => {
  try {
    const movies = await Movie.find().sort({ createdAt: -1 });
    res.json(movies);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/movies/:id/view', async (req, res) => {
  try {
    const movie = await Movie.findByIdAndUpdate(req.params.id, { $inc: { views: 1 } }, { new: true });
    res.json({ success: true, views: movie ? movie.views : 0 });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/request', async (req, res) => {
  try {
    const { title, category, language, seasonEpisode, userName, telegramUsername, userTier } = req.body;
    if (!title || !title.trim()) return res.status(400).json({ success: false, message: 'Title required.' });
    if (!BOT_TOKEN || !LOG_CHANNEL_ID) return res.status(500).json({ success: false, message: 'Log channel not configured.' });

    const logText =
      `📩 <b>NEW CONTENT REQUEST</b>\n\n` +
      `🎬 <b>Title:</b> ${title.trim()}\n` +
      `📂 <b>Category:</b> ${category || 'Movie'}\n` +
      `🌐 <b>Language:</b> ${language || 'Any'}\n` +
      `${seasonEpisode ? `🔢 <b>Season / Ep:</b> ${seasonEpisode}\n` : ''}` +
      `\n👤 <b>User Details:</b>\n` +
      `• <b>Name:</b> ${userName || 'Guest'}\n` +
      `• <b>Telegram:</b> ${telegramUsername ? (telegramUsername.startsWith('@') ? telegramUsername : '@' + telegramUsername) : 'Not Provided'}\n` +
      `• <b>Plan:</b> ${(userTier || 'free').toUpperCase()}`;

    await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: LOG_CHANNEL_ID, text: logText, parse_mode: 'HTML' })
    });

    res.json({ success: true, message: 'Request sent!' });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

app.post('/api/movies', async (req, res) => {
  try {
    const { title, posterUrl, category, language, rating, quality, credit, isPremium, streamUrl, downloadUrl, season, episode, episodeTitle } = req.body;
    const resolvedPoster = await resolvePoster(title, category, posterUrl);
    const selectedCredit = credit || 'Hari_Moviez';
    const isEpisodic = ['series', 'anime'].includes((category || '').toLowerCase()) || episode !== undefined;

    if (isEpisodic && episode !== undefined) {
      const epObj = {
        season: Number(season) || 1,
        episode: Number(episode),
        title: episodeTitle || `Episode ${episode}`,
        streamUrl,
        downloadUrl
      };

      let existingShow = await Movie.findOne({ title: { $regex: new RegExp(`^${title.trim()}$`, 'i') } });

      if (existingShow) {
        const idx = existingShow.episodes.findIndex(e => e.season === epObj.season && e.episode === epObj.episode);
        if (idx > -1) existingShow.episodes[idx] = epObj;
        else existingShow.episodes.push(epObj);

        existingShow.episodes.sort((a, b) => (a.season - b.season) || (a.episode - b.episode));
        if (language) existingShow.language = language;
        if (rating && rating !== 'N/A') existingShow.rating = rating;
        if (quality) existingShow.quality = quality;
        existingShow.credit = selectedCredit;
        if (resolvedPoster && !resolvedPoster.includes('unsplash.com/photo-1536440136628')) {
          existingShow.posterUrl = resolvedPoster;
        }

        await existingShow.save();
        await postToUpdateChannel(existingShow, epObj);
        return res.status(200).json({ success: true, movie: existingShow });
      } else {
        const newShow = new Movie({
          title: title.trim(),
          posterUrl: resolvedPoster,
          category: category || 'Series',
          language: language || 'Multi Audio',
          rating: rating || 'N/A',
          quality: quality || '1080p',
          credit: selectedCredit,
          isPremium: Boolean(isPremium),
          streamUrl,
          downloadUrl,
          episodes: [epObj]
        });
        await newShow.save();
        await postToUpdateChannel(newShow, epObj);
        return res.status(201).json({ success: true, movie: newShow });
      }
    }

    let existingMovie = await Movie.findOne({ title: { $regex: new RegExp(`^${title.trim()}$`, 'i') }, episodes: { $size: 0 } });
    if (existingMovie) {
      existingMovie.posterUrl = resolvedPoster;
      existingMovie.category = category || existingMovie.category;
      existingMovie.language = language || existingMovie.language;
      existingMovie.rating = rating || existingMovie.rating;
      existingMovie.quality = quality || existingMovie.quality;
      existingMovie.credit = selectedCredit;
      existingMovie.isPremium = Boolean(isPremium);
      existingMovie.streamUrl = streamUrl;
      existingMovie.downloadUrl = downloadUrl;
      await existingMovie.save();
      await postToUpdateChannel(existingMovie, null);
      return res.status(200).json({ success: true, movie: existingMovie });
    }

    const newMovie = new Movie({
      title: title.trim(),
      posterUrl: resolvedPoster,
      category: category || 'Action',
      language: language || 'Multi Audio',
      rating: rating || 'N/A',
      quality: quality || '1080p',
      credit: selectedCredit,
      isPremium: Boolean(isPremium),
      streamUrl,
      downloadUrl
    });
    await newMovie.save();
    await postToUpdateChannel(newMovie, null);
    res.status(201).json({ success: true, movie: newMovie });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/download/:id', async (req, res) => {
  try {
    const movie = await Movie.findById(req.params.id);
    if (!movie) return res.status(404).send('Movie not found');
    res.redirect(movie.downloadUrl);
  } catch (err) {
    res.status(500).send('Download error');
  }
});

app.post('/api/user/redeem-key', async (req, res) => {
  try {
    const { key } = req.body;
    if (!key) return res.status(400).json({ success: false, message: "Key required." });

    const keyDoc = await db.collection('vip_keys').findOne({ key: key.trim(), isRedeemed: false });
    if (!keyDoc) return res.status(400).json({ success: false, message: "Invalid or redeemed key." });

    await db.collection('vip_keys').updateOne({ key: key.trim() }, { $set: { isRedeemed: true, redeemedAt: new Date() } });

    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + 30);
    const isVIP = ['standard', 'diamond'].includes(keyDoc.tier);

    await db.collection('users').updateOne(
      { telegramId: keyDoc.telegramId },
      { $set: { tier: keyDoc.tier, isVIP: isVIP, vipExpiry: expiryDate } },
      { upsert: true }
    );

    res.json({ success: true, tier: keyDoc.tier, message: `Activated ${keyDoc.tier.toUpperCase()} Plan!` });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

const botProcess = spawn('python3', ['bot.py']);
botProcess.stdout.on('data', (d) => console.log(`[BOT]: ${d}`));
botProcess.stderr.on('data', (d) => console.error(`[BOT ERROR]: ${d}`));

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`HKM Express Server running on port ${PORT}`));
