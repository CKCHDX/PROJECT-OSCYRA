# SLP Quick Start Guide

**Get started with SLP in 5 minutes!**

---

## Windows Users (Easiest)

### Step 1: Download

```bash
git clone https://github.com/CKCHDX/SLP.git
cd SLP
```

### Step 2: Run Setup Script

**Double-click: `RUNME.bat`**

Or from command line:
```batch
RUNME.bat
```

The script will automatically:
- ✅ Check Python installation
- ✅ Install dependencies
- ✅ Test all encryption layers
- ✅ Show you an interactive menu

### Step 3: Choose What to Do

The menu offers:
1. **Start Secure Server** - Launch encrypted server
2. **Test Secure Client** - Connect with encryption
3. **Build GUI Client** - Create Windows .exe
4. **Run Benchmarks** - Test performance
5. **Auto Test** - Verify everything works

---

## Linux/Mac Users

### Step 1: Clone Repository

```bash
git clone https://github.com/CKCHDX/SLP.git
cd SLP
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install cryptography pynacl
```

### Step 3: Test Encryption

```bash
# Test individual layers
python slp/encryption/aes_layer.py
python slp/encryption/chacha_layer.py
python slp/encryption/noise_layer.py

# Test combined
python slp/encryption/triple_layer.py
```

### Step 4: Run Secure Server

**Terminal 1:**
```bash
python examples/secure_server.py
```

**Terminal 2:**
```bash
python examples/secure_client.py slp://localhost:4270/
```

---

## What Each Option Does

### 1. Secure Server (Production)

```bash
python examples/secure_server.py
```

**Features:**
- ✅ Triple-layer encryption (AES + ChaCha + Noise)
- ✅ Perfect forward secrecy
- ✅ Mutual authentication
- ✅ Production-ready

**Use when:** You want full security

### 2. Basic Server (Testing)

```bash
python examples/server_v2.py
```

**Features:**
- ✅ SLP packet format
- ✅ HTML serving
- ❌ NO encryption

**Use when:** Testing protocol only

### 3. GUI Client

```bash
cd client
build_exe.bat  # Windows
```

**Creates:** `client/dist/SLP_Client.exe`

**Features:**
- ✅ Standalone executable
- ✅ No Python required
- ✅ Modern GUI
- ✅ Browser integration

---

## Testing Checklist

### Basic Protocol Test

```bash
# Terminal 1
python examples/server_v2.py

# Terminal 2
python examples/test_slp.py
```

**Expected:** ✅ Connection successful, HTML received

### Secure Protocol Test

```bash
# Terminal 1
python examples/secure_server.py

# Terminal 2
python examples/secure_client.py
```

**Expected:** 
- ✅ Handshake complete
- ✅ Perfect forward secrecy enabled
- ✅ Encrypted data transfer

### Performance Test

```bash
python examples/benchmark_encryption.py
```

**Expected:**
- Encryption: < 1 ms
- Throughput: > 10 MB/s
- Overhead: ~100 bytes

---

## Common Issues

### "Python not found"

**Solution:** Install Python 3.8+ from [python.org](https://www.python.org/downloads/)

Make sure to check "Add Python to PATH" during installation!

### "Module not found: cryptography"

**Solution:**
```bash
pip install cryptography pynacl
```

### "Permission denied" (Linux)

**Solution:**
```bash
sudo chmod +x RUNME.sh
./RUNME.sh
```

### "Port 4270 already in use"

**Solution:** Kill existing process:

**Windows:**
```batch
netstat -ano | findstr :4270
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
lsof -ti:4270 | xargs kill -9
```

### "Connection timeout"

**Causes:**
1. Server not running
2. Firewall blocking UDP port 4270
3. Wrong address

**Solution:**
1. Start server first
2. Allow UDP 4270 in firewall
3. Check address is correct

---

## File Structure Quick Reference

```
SLP/
├── RUNME.bat              ← START HERE (Windows)
├── QUICKSTART.md          ← You are here
├── SECURITY.md            ← Security details
├── TESTING_GUIDE.md       ← Complete testing guide
│
├── slp/
│   ├── protocol/
│   │   └── packet.py      ← Packet format
│   ├── encryption/
│   │   ├── aes_layer.py   ← Layer 1: AES-256-GCM
│   │   ├── chacha_layer.py← Layer 2: ChaCha20
│   │   ├── noise_layer.py ← Layer 3: Noise Protocol
│   │   └── triple_layer.py← All 3 combined
│   └── client/
│       └── simple_client.py← Client library
│
├── examples/
│   ├── secure_server.py   ← Production server (ENCRYPTED)
│   ├── secure_client.py   ← Production client (ENCRYPTED)
│   ├── server_v2.py       ← Test server (no encryption)
│   ├── test_slp.py        ← Test client (no encryption)
│   └── benchmark_encryption.py ← Performance tests
│
└── client/
    ├── slp_client_gui.py  ← GUI client
    ├── build_exe.bat      ← Build .exe
    └── dist/
        └── SLP_Client.exe ← Standalone executable
```

---

## Next Steps

### 1. Learn the Security

Read: `SECURITY.md` - Understand the encryption layers

### 2. Complete Testing

Read: `TESTING_GUIDE.md` - Run all 8 test scenarios

### 3. Build GUI Client

Run: `client/build_exe.bat` - Create Windows executable

### 4. Integrate with Qt

Use `slp.client.simple_client` in your Qt WebEngine browser

### 5. Deploy to Production

Use `examples/secure_server.py` with proper configuration

---

## Support

- **Documentation**: Check `SECURITY.md` and `TESTING_GUIDE.md`
- **Issues**: Create GitHub issue
- **Security**: security@oscyra.solutions

---

## Summary

**To get started right now:**

1. Run `RUNME.bat` (Windows) or install deps manually
2. Choose option 7 (Auto Test) to verify everything works
3. Choose option 1 (Secure Server) to start server
4. Choose option 2 (Secure Client) to test connection
5. Done! You have military-grade encryption working!

**Total time: 5 minutes**

---

*Last Updated: March 8, 2026*  
*Version: 1.0.0*  
*Ready to use: ✅ YES*
