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

const movieSchema = new mongoose.Schema({
  title: { type: String, required: true },
  posterUrl: { type: String, default: 'https://via.placeholder.com/300x450?text=HKM+Providers' },
  category: { type: String, default: 'Action' },
  quality: { type: String, default: '1080p' },
  isPremium: { type: Boolean, default: false },
  views: { type: Number, default: 0 },
  tgMessageId: { type: Number },
  tgFileId: { type: String },
  streamUrl: { type: String, required: true },
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

app.post('/api/movies', async (req, res) => {
  try {
    const { title, posterUrl, category, quality, isPremium, tgMessageId, tgFileId, streamUrl } = req.body;
    const newMovie = new Movie({ title, posterUrl, category, quality, isPremium, tgMessageId, tgFileId, streamUrl });
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
    res.setHeader('Content-Disposition', `attachment; filename="${movie.title}.mp4"`);
    res.setHeader('Content-Type', 'video/mp4');
    res.redirect(movie.streamUrl);
  } catch (err) {
    res.status(500).send('Download error');
  }
});

// VIP Key Redemption Endpoint
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
