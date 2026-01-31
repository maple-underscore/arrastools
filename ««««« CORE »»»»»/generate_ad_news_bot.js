#!/usr/bin/env node
// Generate arrascopypasta_ad_news.js with ad_news.txt entries embedded

const fs = require('fs');
const path = require('path');

const adNewsPath = path.join(__dirname, '..', 'copypastas', 'ad_news.txt');
const outputPath = path.join(__dirname, 'arrascopypasta_ad_news.js');

if (!fs.existsSync(adNewsPath)) {
  console.error(`Error: ${adNewsPath} not found!`);
  console.log('Run "node news.js" first to generate ad_news.txt');
  process.exit(1);
}

const adNewsContent = fs.readFileSync(adNewsPath, 'utf8');
const lines = adNewsContent.split('\n').filter(line => line.trim());

console.log(`Loaded ${lines.length} entries from ad_news.txt`);

const jsTemplate = `// Arras.io Ad News Copypasta Bot
// Paste this into browser console to run
// Press Ctrl+C in console to stop

(function() {
  'use strict';

// Ensure window.addEventListener hooks are installed for input simulation
let windowListener = window.addEventListener;
window.addEventListener = function(...args) {
  let type = args[0];
  if (type === "keydown" || type === "keyup" || type === "mousedown" || type === "mouseup") {
    let callback = args[1];
    args[1] = function(event) {
      return callback.call(this, {
        isTrusted: true,
        key: event.key,
        code: event.code,
        preventDefault: function(){}
      });
    };
  }
  return windowListener.apply(this, args);
}

function keyEvent(key, type) {
  try {
    const eventType = type ? "keydown" : "keyup";
    const eventInit = {
      key: key,
      code: key,
      keyCode: key === "Enter" ? 13 : 0,
      which: key === "Enter" ? 13 : 0,
      bubbles: true,
      cancelable: true,
      composed: true
    };
    
    // Find canvas element (game usually listens on canvas)
    const canvas = document.querySelector('canvas');
    
    // Dispatch to all available targets
    if (canvas) {
      canvas.dispatchEvent(new KeyboardEvent(eventType, eventInit));
    } else {
      console.warn("Canvas not found for keyEvent");
    }
    
    if (document) {
      document.dispatchEvent(new KeyboardEvent(eventType, eventInit));
    }
    
    if (document.body) {
      document.body.dispatchEvent(new KeyboardEvent(eventType, eventInit));
    }
    
    if (window) {
      window.dispatchEvent(new KeyboardEvent(eventType, eventInit));
    }
    
    console.log(`Key event: ${key} ${eventType}`);
  } catch (e) {
    console.error("Error in keyEvent:", e);
  }
}

function clickCanvasAt(x, y) {
  const canvas = document.querySelector('canvas');
  if (!canvas) {
    return false;
  }
  const rect = canvas.getBoundingClientRect();
  const clientX = rect.left + x;
  const clientY = rect.top + y;
  const down = new MouseEvent('mousedown', { bubbles: true, clientX, clientY, button: 0 });
  const up = new MouseEvent('mouseup', { bubbles: true, clientX, clientY, button: 0 });
  canvas.dispatchEvent(down);
  canvas.dispatchEvent(up);
  return true;
}

async function chat(msg) {
  return new Promise(async (resolve) => {
    // First, press Enter to open chat
    console.log("Opening chat...");
    keyEvent("Enter", true);
    await new Promise(r => setTimeout(r, 50));
    keyEvent("Enter", false);
    
    // Wait up to 10 seconds for chat input to appear
    let input = null;
    const startTime = Date.now();
    while (!input && Date.now() - startTime < 10000) {
      await new Promise(r => setTimeout(r, 200));
      input = document.querySelector("input:not([id])");
    }

    // If still no input, attempt reconnect clicks every second
    if (!input) {
      console.log("No chat input after 10s. Attempting reconnect clicks...");
      while (!input) {
        const canvas = document.querySelector('canvas');
        if (canvas) {
          const rect = canvas.getBoundingClientRect();
          const canvasW = rect.width;
          const canvasH = rect.height;
          const clickX = canvasW * 0.55;
          const clickY = canvasH * 0.629;
          clickCanvasAt(clickX, clickY);
          console.log("Reconnect click sent");
        }

        // After reconnecting, press Enter again to open chat
        await new Promise(r => setTimeout(r, 1000));
        keyEvent("Enter", true);
        await new Promise(r => setTimeout(r, 50));
        keyEvent("Enter", false);
        await new Promise(r => setTimeout(r, 200));
        input = document.querySelector("input:not([id])");
      }
    }
    
    // Chat is now open, type the message
    console.log("Typing message...");
    input.focus();
    input.value = msg;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    
    // Wait a bit, then press Enter to send the message
    await new Promise(r => setTimeout(r, 100));
    console.log("Sending message...");
    keyEvent("Enter", true);
    await new Promise(r => setTimeout(r, 50));
    keyEvent("Enter", false);
    
    resolve(true);
  });
}

function pause() {
  return new Promise((resolve) => {
    setTimeout(resolve, 3050); // 3.05 second delay between messages
  });
}

// Split text into chunks of max 60 chars, breaking at word boundaries
function splitText(text, maxLength = 60) {
  const chunks = [];
  const words = text.split(' ');
  let buffer = "";
  
  for (const word of words) {
    if (buffer) {
      if (buffer.length + 1 + word.length > maxLength) {
        chunks.push(buffer);
        buffer = word;
      } else {
        buffer += " " + word;
      }
    } else {
      if (word.length > maxLength) {
        chunks.push(word.substring(0, maxLength));
        buffer = word.substring(maxLength);
      } else {
        buffer = word;
      }
    }
  }
  
  if (buffer) {
    chunks.push(buffer);
  }
  
  return chunks;
}

// Ad news entries from ad_news.txt
const AD_NEWS = ${JSON.stringify(lines, null, 2)};

async function runAdNewsBot() {
  console.log(\`Loaded \${AD_NEWS.length} ad_news entries\`);
  console.log("Starting ad_news copypasta bot in 5 seconds...");
  console.log("Press Ctrl+C or close console to stop");
  
  // Wait 5 seconds before starting
  await new Promise(resolve => setTimeout(resolve, 5000));
  console.log("Bot starting now!");
  
  while (true) {
    // Pick a random entry
    const randomEntry = AD_NEWS[Math.floor(Math.random() * AD_NEWS.length)];
    
    // Split into 60-char chunks with word breaks
    const chunks = splitText(randomEntry, 60);
    
    // Type each chunk
    for (const chunk of chunks) {
      await chat(chunk);
      await pause();
    }
  }
}

// Start the bot
console.log("=== Arras.io Ad News Copypasta Bot ===");
console.log("Initializing...");
runAdNewsBot().catch(err => {
  console.error("Bot error:", err);
});

})(); // End IIFE
`;

fs.writeFileSync(outputPath, jsTemplate, 'utf8');
console.log(`Generated ${outputPath}`);
console.log(`File size: ${(fs.statSync(outputPath).size / 1024).toFixed(2)} KB`);
console.log('\nTo use:');
console.log('1. Open Arras.io in your browser');
console.log('2. Open browser console (F12)');
console.log(`3. Copy and paste the contents of ${path.basename(outputPath)}`);
console.log('4. Press Enter to start the bot');
