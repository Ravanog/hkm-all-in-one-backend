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

// Launch Python Bot process alongside Express
const botProcess = spawn('python3', ['bot.py']);
botProcess.stdout.on('data', (d) => console.log(`[BOT]: ${d}`));

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => console.log(`HKM Express Server running on port ${PORT}`));
