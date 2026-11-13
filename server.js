const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const { spawn } = require('child_process');

const app = express();
app.use(cors());
app.use(express.json());

const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/hkmdb';
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
  posterUrl: { type: String, default: 'https://via.placeholder.com/300x450?text=HKM+Providers' },
  category: { type: String, default: 'Action' },
  quality: { type: String, default: '1080p' },
  isPremium: { type: Boolean, default: false },
  views: { type: Number, default: 0 },
  streamUrl: { type: String, default: '' },
  downloadUrl: { type: String, default: '' },
  episodes: [episodeSchema],
  createdAt: { type: Date, default: Date.now }
});
const Movie = mongoose.model('Movie', movieSchema);

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

// Supports both standalone Movies and Episode-wise Series/Anime
app.post('/api/movies', async (req, res) => {
  try {
    const { title, posterUrl, category, quality, isPremium, streamUrl, downloadUrl, season, episode, episodeTitle } = req.body;
    const isEpisodic = ['series', 'anime'].includes((category || '').toLowerCase()) || episode !== undefined;

    if (isEpisodic && episode !== undefined) {
      const epObj = {
        season: Number(season) || 1,
        episode: Number(episode),
        title: episodeTitle || `Episode ${episode}`,
        streamUrl,
        downloadUrl
      };

      // Check if Series/Anime already exists (case-insensitive)
      let existingShow = await Movie.findOne({ title: { $regex: new RegExp(`^${title.trim()}$`, 'i') } });

      if (existingShow) {
        // Replace existing episode if same season & episode, otherwise push
        const idx = existingShow.episodes.findIndex(e => e.season === epObj.season && e.episode === epObj.episode);
        if (idx > -1) {
          existingShow.episodes[idx] = epObj;
        } else {
          existingShow.episodes.push(epObj);
        }
        existingShow.episodes.sort((a, b) => (a.season - b.season) || (a.episode - b.episode));
        if (posterUrl && !posterUrl.includes('unsplash.com/photo-1536440136628')) {
          existingShow.posterUrl = posterUrl;
        }
        await existingShow.save();
        return res.status(200).json({ success: true, movie: existingShow });
      } else {
        const newShow = new Movie({
          title: title.trim(),
          posterUrl,
          category: category || 'Series',
          quality,
          isPremium,
          streamUrl,
          downloadUrl,
          episodes: [epObj]
        });
        await newShow.save();
        return res.status(201).json({ success: true, movie: newShow });
      }
    }

    // Standard single Movie
    const newMovie = new Movie({ title: title.trim(), posterUrl, category, quality, isPremium, streamUrl, downloadUrl });
    await newMovie.save();
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
    if (!key) return res.status(400).json({ success: false, message: "Key is required." });

    const keyDoc = await db.collection('vip_keys').findOne({ key: key.trim(), isRedeemed: false });
    if (!keyDoc) {
      return res.status(400).json({ success: false, message: "Invalid or already redeemed key." });
    }

    await db.collection('vip_keys').updateOne(
      { key: key.trim() }, 
      { $set: { isRedeemed: true, redeemedAt: new Date() } }
    );

    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + 30);
    const isVIP = ['standard', 'diamond'].includes(keyDoc.tier);

    await db.collection('users').updateOne(
      { telegramId: keyDoc.telegramId },
      { $set: { tier: keyDoc.tier, isVIP: isVIP, vipExpiry: expiryDate } },
      { upsert: true }
    );

    res.json({ 
      success: true, 
      tier: keyDoc.tier, 
      telegramId: keyDoc.telegramId,
      message: `Successfully activated ${keyDoc.tier.toUpperCase()} Plan!` 
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

const botProcess = spawn('python3', ['bot.py']);
botProcess.stdout.on('data', (d) => console.log(`[BOT]: ${d}`));

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => console.log(`HKM Express Server running on port ${PORT}`));
