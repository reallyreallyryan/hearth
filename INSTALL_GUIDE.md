# Hearth Installation Guide

Hearth gives your AI a persistent memory. You install it once, and every AI tool you use — Claude Desktop, LM Studio, Cursor — can remember things across conversations.

---

## What You Need

### Required: Python 3.11 or newer

Open **Terminal** (search "Terminal" in Spotlight) and paste this:

```
python3 --version
```

You should see something like:

```
Python 3.12.12
```

If you see `command not found` or a version below 3.11, install Python from:
https://www.python.org/downloads/

### Optional: Ollama (for smarter search)

Ollama runs a small AI model on your computer that makes Hearth's search much better. It's free and private — nothing leaves your machine.

Check if you have it:

```
ollama --version
```

If you see `command not found`, you can install it from https://ollama.ai — it's a normal Mac app, just download and open it.

If you don't want Ollama, that's fine. Hearth works without it (search will use keywords instead of meaning).

---

## Step 1: Download Hearth

In Terminal, paste these two lines:

```
git clone https://github.com/reallyreallyryan/hearth.git
cd hearth
```

You should now be inside the `hearth` folder.

---

## Step 2: Install Hearth

Paste this:

```
pip install -e ".[transcribe]"
```

This installs Hearth with audio transcription support (faster-whisper). If you don't need audio transcription, `pip install -e .` works too.

You'll see it download some dependencies. This takes about 30 seconds.

When it's done, verify it worked:

```
hearth --version
```

You should see:

```
hearth, version 0.1.0
```

**If you see `command not found`:** Try `pip3 install -e ".[transcribe]"` instead, then use `hearth --version` again.

---

## Step 3: Set Up Your Memory

Paste this:

```
hearth init
```

This creates your memory database and downloads the embedding model (about 274MB).

You should see something like:

```
Initializing Hearth...

  Disk:      500.0 GB free
  Directory: /Users/you/hearth
  Config:    /Users/you/hearth/config.yaml (created)
  Database:  /Users/you/hearth/hearth.db

  Ollama:    nomic-embed-text (ready)

==================================================
Hearth is ready!
```

**If you skipped Ollama**, use this instead:

```
hearth init --no-models
```

You'll see "Ollama: skipped" instead, which is totally fine.

---

## Step 4: Test It

Let's store your first memory. Paste this:

```
hearth remember "I prefer dark mode in all my apps"
```

You should see:

```
Stored memory a1b2c3d4... with embedding
```

(The letters/numbers will be different — that's the memory's ID.)

Now search for it:

```
hearth search "what theme do I like"
```

You should see your memory come back as a search result, even though you used different words.

Check your stats:

```
hearth status
```

You should see:

```
Hearth v0.1.0
Database: /Users/you/hearth/hearth.db

Memories:   1 active, 0 archived
Embeddings: 1 (0 pending)
Projects:   0 active
...
```

---

## Step 4b: Test Audio Transcription

If you installed with `[transcribe]`, you can transcribe audio files locally. Grab any audio file (voice memo, podcast clip, etc.) and try:

```
hearth transcribe ~/path/to/audio.m4a --model base --segments
```

You should see timestamped text output. The first run downloads the Whisper model (~145MB for base).

To transcribe AND store it as a searchable memory:

```
hearth ingest ~/path/to/audio.m4a --model base
```

Then search for it:

```
hearth search "something from the audio"
```

The transcribed text is now stored in your Hearth database, searchable by meaning — from Terminal, Claude Desktop, or LM Studio.

---

## Step 5: Connect to Claude Desktop

This is where it gets powerful. After this step, Claude will remember things you tell it — across conversations, forever.

### 5a. Find the config file

Paste this to open the config file:

```
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**If it says the file doesn't exist**, create it:

```
mkdir -p ~/Library/Application\ Support/Claude
touch ~/Library/Application\ Support/Claude/claude_desktop_config.json
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 5b. Find the full path to hearth

Claude Desktop can't find commands installed by pyenv, nvm, etc. You need the **full path**. Paste this in Terminal:

```
which hearth
```

You'll get something like:

```
/Users/you/.pyenv/versions/3.12.12/bin/hearth
```

Copy that path — you'll need it in the next step.

**Shortcut:** `hearth init` prints the correct config with the full path already filled in. Scroll up and copy it from there.

### 5c. Add the Hearth config

The config file will open in TextEdit (or your default editor). Replace whatever is in there with this, **but replace the path with YOUR path from step 5b**:

```json
{
  "mcpServers": {
    "hearth": {
      "command": "/Users/you/.pyenv/versions/3.12.12/bin/hearth",
      "args": ["serve"]
    }
  }
}
```

**Important:** If you already have other MCP servers in this file, don't replace everything. Just add the `"hearth": { ... }` block inside the existing `"mcpServers"` section, with a comma separating it from the others.

Save the file and close it.

### 5d. Restart Claude Desktop

You need to fully quit and reopen Claude Desktop:

1. Click **Claude** in the menu bar at the top of your screen
2. Click **Quit Claude** (or press Cmd+Q)
3. Open Claude Desktop again from your Applications folder or Spotlight

### 5e. Verify it worked

When Claude Desktop opens, got to Settings > Connectors > hearth. Click it — you should see a list of Hearth tools:

- memory_store
- memory_search
- memory_list
- memory_update
- memory_delete
- project_create
- project_list
- project_get
- project_update
- project_archive
- hearth_status
- hearth_export

If you see these, Hearth is connected.

---

## Step 6: Test with Claude Desktop

Try typing these into Claude Desktop:

**Store a memory:**

> Remember that my favorite programming language is Rust and I'm currently building a project called Beacon.

Claude should call `memory_store` and confirm it saved.

**Search your memory:**

> What's my favorite programming language?

Claude should call `memory_search` and tell you "Rust."

**Create a project:**

> Create a Hearth project called "beacon" with description "A distributed messaging system I'm building in Rust"

Claude should call `project_create`.

---

## Step 7: Prove It Works Across Tools

This is the magic moment. Go back to Terminal and paste:

```
hearth search "programming language"
```

You should see the memory that Claude stored — even though you're searching from Terminal, not Claude Desktop. The memory lives in one place, and every tool can access it.

```
hearth status
```

Should now show more memories than before.

---

## Step 8: Connect to LM Studio

LM Studio also supports MCP servers. After this step, any model you run in LM Studio will have access to the same memories as Claude Desktop.

### 8a. Open the MCP config file

LM Studio's MCP config is at `~/.lmstudio/mcp.json`. Open it:

```
open ~/.lmstudio/mcp.json
```

**If it says the file doesn't exist**, create it:

```
mkdir -p ~/.lmstudio
echo '{"mcpServers": {}}' > ~/.lmstudio/mcp.json
open ~/.lmstudio/mcp.json
```

### 8b. Find your hearth path

Same as Claude Desktop — you need the full path. If you already have it from Step 5b, use that. Otherwise:

```
which hearth
```

### 8c. Add the Hearth config

Edit the file to look like this, **using YOUR path from step 8b**:

```json
{
  "mcpServers": {
    "hearth": {
      "command": "/Users/you/.pyenv/versions/3.12.12/bin/hearth",
      "args": ["serve"]
    }
  }
}
```

**If you already have other MCP servers** in this file, add the `"hearth": { ... }` block inside the existing `"mcpServers"` section, with a comma separating it from the others.

Save the file and close it.

### 8d. Restart LM Studio

Fully quit LM Studio (Cmd+Q) and reopen it.

### 8e. Verify it worked

1. Open LM Studio and load any model
2. Start a new chat
3. Look for an MCP tools indicator — LM Studio should show that Hearth's tools are available
4. Try asking the model:

> What memories do I have stored?

The model should call `memory_list` or `memory_search` and return your stored memories — including anything you saved from Claude Desktop or Terminal.

### 8f. Test cross-client persistence

This is the real proof. If you stored a memory in Claude Desktop earlier:

> What's my favorite programming language?

LM Studio should find the same "Rust" memory that Claude stored. One memory system, three different tools (Terminal, Claude Desktop, LM Studio) — all sharing the same data.

---

## Troubleshooting

### `command not found: hearth`

Your terminal can't find the hearth command. Try:

```
pip3 install -e .
```

If that doesn't work, you may need to add Python's bin directory to your PATH. This is a Python installation issue, not a Hearth issue.

### Claude Desktop doesn't show the tools

1. Make sure you saved the config file (Step 5b)
2. Make sure you fully quit Claude Desktop with Cmd+Q (not just closed the window)
3. Check the config file has valid JSON — even a missing comma will break it
4. Try pasting the config again carefully

### `Ollama: not running`

Ollama needs to be running in the background. Open the Ollama app from your Applications folder — it runs in the menu bar. Then try `hearth init` again.

### `Ollama: not installed` but I don't want it

That's fine! Use:

```
hearth init --no-models
```

Everything works without Ollama. You just won't get semantic search (search by meaning). Keyword search still works great.

### Search returns no results

If you used `--no-models` and Ollama isn't running, search uses keywords only. Try searching for exact words that are in your memory, not paraphrases.

### I want to start over

To completely reset Hearth:

```
rm -rf ~/hearth
hearth init
```

This deletes all your memories and starts fresh.

---

## Where Your Data Lives

Everything is in one folder: `~/hearth/`

```
~/hearth/
  hearth.db       <- All your memories (this is the important file)
  config.yaml     <- Your settings
```

To back up your memories, just copy `hearth.db` somewhere safe. To move to a new computer, copy the whole `~/hearth/` folder.

---

## Uninstall

To completely remove Hearth:

```
pip uninstall hearth-memory -y
rm -rf ~/hearth
```

This removes the command and all your data.
