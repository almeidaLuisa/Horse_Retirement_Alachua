import 'dotenv/config';
import path from 'node:path';
import fs from 'node:fs/promises';
import express from 'express';
import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';

const app = express();

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const MONGODB_URI = process.env.MONGODB_URI;

if (!MONGODB_URI) {
  console.error('Missing MONGODB_URI. Create a .env file (see .env.example).');
  process.exit(1);
}

try {
  console.log('Connecting to MongoDB...');
  await mongoose.connect(MONGODB_URI, { serverSelectionTimeoutMS: 5000 });
  console.log('MongoDB connected.');
} catch (err) {
  console.error('MongoDB connection failed. Check that MongoDB is running or update MONGODB_URI in .env');
  console.error(err?.message || err);
  process.exit(1);
}

const userSchema = new mongoose.Schema(
  {
    email: { type: String, required: true, unique: true, lowercase: true, trim: true },
    passwordHash: { type: String, required: true }
  },
  { timestamps: true }
);

const User = mongoose.model('User', userSchema);

app.use(express.json());

// Static files
const rootDir = process.cwd();
app.use('/', express.static(path.join(rootDir, 'frontend')));
app.use('/images', express.static(path.join(rootDir, 'images')));

// List images for gallery
app.get('/api/images', async (req, res) => {
  try {
    const imagesDir = path.join(rootDir, 'images');
    const entries = await fs.readdir(imagesDir, { withFileTypes: true });
    const images = entries
      .filter(e => e.isFile())
      .map(e => e.name)
      .filter(name => /\.(jpe?g|png|gif|webp)$/i.test(name))
      .sort((a, b) => a.localeCompare(b));

    res.json({ images });
  } catch (err) {
    res.status(500).json({ error: 'Unable to list images' });
  }
});

// Register
app.post('/api/auth/register', async (req, res) => {
  try {
    const email = String(req.body?.email || '').trim().toLowerCase();
    const password = String(req.body?.password || '');

    if (!email || !password) return res.status(400).json({ error: 'Email and password are required.' });
    if (password.length < 6) return res.status(400).json({ error: 'Password must be at least 6 characters.' });

    const existing = await User.findOne({ email }).lean();
    if (existing) return res.status(409).json({ error: 'Email already registered.' });

    const passwordHash = await bcrypt.hash(password, 10);
    await User.create({ email, passwordHash });

    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: 'Registration failed.' });
  }
});

// Login
app.post('/api/auth/login', async (req, res) => {
  try {
    const email = String(req.body?.email || '').trim().toLowerCase();
    const password = String(req.body?.password || '');

    if (!email || !password) return res.status(400).json({ error: 'Email and password are required.' });

    const user = await User.findOne({ email });
    if (!user) return res.status(401).json({ error: 'Invalid email or password.' });

    const ok = await bcrypt.compare(password, user.passwordHash);
    if (!ok) return res.status(401).json({ error: 'Invalid email or password.' });

    // Minimal demo token (NOT a secure auth token). Good enough to show integration.
    // For real auth, use JWT + httpOnly cookies.
    const token = Buffer.from(`${user._id}:${Date.now()}`).toString('base64url');

    res.json({ ok: true, token });
  } catch (err) {
    res.status(500).json({ error: 'Login failed.' });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log('Open: http://localhost:' + PORT + '/home_page.html');
});
