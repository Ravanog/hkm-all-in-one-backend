const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const { spawn } = require('child_process');

const app = express();
app.use(cors());
app.use(express.json());

const MONGO_URI = process.env.MONGO_URI || 'mongodb+srv://anikush8310_db_user:nPoB0GWMD34X7aeR@cluster0.yvanywe.mongodb.net';
const TMDB_API_KEY = process.env.TMDB_API_KEY || '6abcb6bb99fb77f33c37016a28866ed2';

mongoose.connect(MONGO_URI)
  .then(() => console.log('HKM Database Connected'))
  .catch(err => console.error('MongoDB Error:', err));

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

app.get('/', (req, res) => {
  res.status(200).send('HKM Backend & Bot System is active and running!');
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
    res.status(201).json({ success: true, movie: newMovie });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/movies/:id', async (req, res) => {
  try {
    const deletedMovie = await Movie.findByIdAndDelete(req.params.id);
    if (!deletedMovie) return res.status(404).json({ success: false, message: 'Movie not found' });
    res.json({ success: true, message: 'Movie deleted successfully' });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Spawn Python Bot concurrently
const botProcess = spawn('python3', ['bot.py']);
botProcess.stdout.on('data', (d) => console.log(`[BOT OUT]: ${d.toString().trim()}`));
botProcess.stderr.on('data', (d) => console.error(`[BOT ERR]: ${d.toString().trim()}`));
botProcess.on('close', (code) => console.log(`[BOT]: Child process exited with code ${code}`));

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`HKM Express Server running on port ${PORT}`));
