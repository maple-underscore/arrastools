// ==UserScript==
// @name         Arras.io Lag Cluster Detector
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Detects and highlights lag-inducing entity clusters using actual game entity data
// @author       Your Name
// @match        https://*.arras.io/*
// @match        https://arras.io/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
  'use strict';

  // ============================================================================
  // Configuration
  // ============================================================================
  const CONFIG = {
    enabled: true,
    cellSize: 50,           // Grid cell width/height in pixels
    threshold: 100,         // Minimum entity count to highlight
    updateInterval: 150,    // Update frequency in ms
    showCounts: true,       // Display entity counts on cells
    clusterColor: 'rgba(255, 0, 0, 0.3)',
    clusterBorderColor: 'rgba(255, 0, 0, 0.8)',
    clusterBorderWidth: 2,
    textColor: '#FF0000',
  };

  // ============================================================================
  // Overlay Canvas Setup
  // ============================================================================
  let overlayCanvas = null;
  let overlayCtx = null;
  let panelContainer = null;

  function createOverlay() {
    if (overlayCanvas) return;

    overlayCanvas = document.createElement('canvas');
    overlayCanvas.id = 'arras-cluster-detector-overlay';
    overlayCanvas.style.position = 'fixed';
    overlayCanvas.style.top = '0';
    overlayCanvas.style.left = '0';
    overlayCanvas.style.zIndex = '2147483647'; // max safe integer for CSS
    overlayCanvas.style.pointerEvents = 'none';
    overlayCanvas.width = window.innerWidth;
    overlayCanvas.height = window.innerHeight;

    document.body.appendChild(overlayCanvas);
    overlayCtx = overlayCanvas.getContext('2d');

    // Resize canvas on window resize
    window.addEventListener('resize', () => {
      overlayCanvas.width = window.innerWidth;
      overlayCanvas.height = window.innerHeight;
    });
  }

  // ============================================================================
  // Control Panel
  // ============================================================================
  function createControlPanel() {
    if (panelContainer) return;

    panelContainer = document.createElement('div');
    panelContainer.id = 'arras-cluster-panel';
    panelContainer.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: rgba(0, 0, 0, 0.8);
      color: #fff;
      padding: 12px;
      border-radius: 6px;
      font-family: monospace;
      font-size: 12px;
      z-index: 10000;
      min-width: 220px;
      border: 1px solid rgba(255, 0, 0, 0.5);
    `;

    const html = `
      <div style="margin-bottom: 8px; font-weight: bold; color: #ff6666;">Lag Cluster Detector</div>
      
      <label style="display: flex; align-items: center; margin-bottom: 6px; cursor: pointer;">
        <input type="checkbox" id="cluster-enabled" ${CONFIG.enabled ? 'checked' : ''} 
               style="margin-right: 6px; cursor: pointer;">
        <span>Enabled</span>
      </label>
      
      <div style="margin-bottom: 6px;">
        <label>Cell Size: <span id="cluster-cell-display">${CONFIG.cellSize}</span>px</label>
        <input type="range" id="cluster-cell-size" min="20" max="150" step="5" 
               value="${CONFIG.cellSize}" style="width: 100%; cursor: pointer;">
      </div>
      
      <div style="margin-bottom: 6px;">
        <label>Threshold: <span id="cluster-threshold-display">${CONFIG.threshold}</span></label>
        <input type="range" id="cluster-threshold" min="10" max="500" step="10" 
               value="${CONFIG.threshold}" style="width: 100%; cursor: pointer;">
      </div>
      
      <label style="display: flex; align-items: center; margin-bottom: 6px; cursor: pointer;">
        <input type="checkbox" id="cluster-show-counts" ${CONFIG.showCounts ? 'checked' : ''} 
               style="margin-right: 6px; cursor: pointer;">
        <span>Show Counts</span>
      </label>
      
      <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.2);">
        <div style="color: #888; font-size: 11px;">Active Clusters: <span id="cluster-count">0</span></div>
      </div>
    `;

    panelContainer.innerHTML = html;
    document.body.appendChild(panelContainer);

    // Event listeners
    document.getElementById('cluster-enabled').addEventListener('change', (e) => {
      CONFIG.enabled = e.target.checked;
    });

    document.getElementById('cluster-cell-size').addEventListener('input', (e) => {
      CONFIG.cellSize = parseInt(e.target.value);
      document.getElementById('cluster-cell-display').textContent = CONFIG.cellSize;
    });

    document.getElementById('cluster-threshold').addEventListener('input', (e) => {
      CONFIG.threshold = parseInt(e.target.value);
      document.getElementById('cluster-threshold-display').textContent = CONFIG.threshold;
    });

    document.getElementById('cluster-show-counts').addEventListener('change', (e) => {
      CONFIG.showCounts = e.target.checked;
    });
  }

  // ============================================================================
  // Entity Access & Game Viewport Detection
  // ============================================================================
  function getGameViewport() {
    // Try to find game canvas or viewport dimensions
    const canvas = document.querySelector('canvas');
    if (canvas) {
      return {
        x: 0,
        y: 0,
        width: canvas.clientWidth,
        height: canvas.clientHeight,
      };
    }
    return {
      x: 0,
      y: 0,
      width: window.innerWidth,
      height: window.innerHeight,
    };
  }

  function getGameEntities() {
    if (window.game && window.game.entities) {
        const ents = window.game.entities;
        if (Array.isArray(ents)) return ents;
        return Object.values(ents);
    }
    return [];
  }


  function getGameCameraOffset() {
    // Try to get camera position from game state
    if (window.game && window.game.camera) {
      return {
        x: window.game.camera.x || 0,
        y: window.game.camera.y || 0,
      };
    }

    // Fallback: Check for player tank position
    if (window.game && window.game.myTank) {
      return {
        x: window.game.myTank.x || 0,
        y: window.game.myTank.y || 0,
      };
    }

    return { x: 0, y: 0 };
  }

  // ============================================================================
  // Spatial Clustering
  // ============================================================================
  function buildSpatialGrid(entities, cellSize) {
    const grid = new Map();

    for (const entity of entities) {
      if (!entity.x || !entity.y) continue;

      const cellX = Math.floor(entity.x / cellSize);
      const cellY = Math.floor(entity.y / cellSize);
      const key = `${cellX},${cellY}`;

      if (!grid.has(key)) {
        grid.set(key, {
          x: cellX,
          y: cellY,
          count: 0,
          entities: [],
        });
      }

      const cell = grid.get(key);
      cell.count++;
      cell.entities.push(entity);
    }

    return grid;
  }

  function identifyHighDensityCells(grid, threshold) {
    const highDensity = [];

    for (const cell of grid.values()) {
      if (cell.count >= threshold) {
        highDensity.push(cell);
      }
    }

    return highDensity;
  }

  function mergeAdjacentCells(cells) {
    if (cells.length === 0) return [];

    const visited = new Set();
    const clusters = [];

    for (const cell of cells) {
      const key = `${cell.x},${cell.y}`;
      if (visited.has(key)) continue;

      // BFS to merge adjacent cells
      const cluster = [];
      const queue = [cell];
      visited.add(key);

      while (queue.length > 0) {
        const current = queue.shift();
        cluster.push(current);

        // Check 8 neighbors
        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            if (dx === 0 && dy === 0) continue;
            const nx = current.x + dx;
            const ny = current.y + dy;
            const nkey = `${nx},${ny}`;

            if (!visited.has(nkey)) {
              const neighbor = cells.find(c => c.x === nx && c.y === ny);
              if (neighbor) {
                visited.add(nkey);
                queue.push(neighbor);
              }
            }
          }
        }
      }

      clusters.push(cluster);
    }

    return clusters;
  }

  function getCluterBounds(cluster, cellSize) {
    if (cluster.length === 0) return null;

    let minX = cluster[0].x;
    let maxX = cluster[0].x;
    let minY = cluster[0].y;
    let maxY = cluster[0].y;

    for (const cell of cluster) {
      minX = Math.min(minX, cell.x);
      maxX = Math.max(maxX, cell.x);
      minY = Math.min(minY, cell.y);
      maxY = Math.max(maxY, cell.y);
    }

    return {
      worldX: minX * cellSize,
      worldY: minY * cellSize,
      worldX2: (maxX + 1) * cellSize,
      worldY2: (maxY + 1) * cellSize,
      totalCount: cluster.reduce((sum, cell) => sum + cell.count, 0),
    };
  }

  // ============================================================================
  // World to Screen Conversion
  // ============================================================================
  function worldToScreen(worldX, worldY, cameraOffset, canvas) {
    const relativeX = worldX - cameraOffset.x;
    const relativeY = worldY - cameraOffset.y;

    const cam = window.game.camera;
    const scale = cam.scale;

    const screenX = overlayCanvas.width / 2 + (worldX - cam.x) * scale;
    const screenY = overlayCanvas.height / 2 + (worldY - cam.y) * scale;

    return { x: screenX, y: screenY };
  }

  // ============================================================================
  // Rendering
  // ============================================================================
  function renderClusters(clusters, cellSize, cameraOffset) {
    if (!overlayCtx || !CONFIG.enabled) {
      overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
      return;
    }

    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    let clusterCount = 0;

    for (const cluster of clusters) {
      const bounds = getCluterBounds(cluster, cellSize);
      if (!bounds) continue;

      clusterCount++;

      // Convert world coordinates to screen coordinates
      const topLeft = worldToScreen(bounds.worldX, bounds.worldY, cameraOffset, overlayCanvas);
      const bottomRight = worldToScreen(bounds.worldX2, bounds.worldY2, cameraOffset, overlayCanvas);

      const screenWidth = bottomRight.x - topLeft.x;
      const screenHeight = bottomRight.y - topLeft.y;

      // Draw filled rectangle
      overlayCtx.fillStyle = CONFIG.clusterColor;
      overlayCtx.fillRect(topLeft.x, topLeft.y, screenWidth, screenHeight);

      // Draw border
      overlayCtx.strokeStyle = CONFIG.clusterBorderColor;
      overlayCtx.lineWidth = CONFIG.clusterBorderWidth;
      overlayCtx.strokeRect(topLeft.x, topLeft.y, screenWidth, screenHeight);

      // Draw count if enabled
      if (CONFIG.showCounts && bounds.totalCount > 0) {
        overlayCtx.fillStyle = CONFIG.textColor;
        overlayCtx.font = 'bold 12px monospace';
        overlayCtx.textAlign = 'center';
        overlayCtx.textBaseline = 'middle';

        const centerX = topLeft.x + screenWidth / 2;
        const centerY = topLeft.y + screenHeight / 2;

        overlayCtx.fillText(bounds.totalCount.toString(), centerX, centerY);
      }
    }

    // Update panel
    const countDisplay = document.getElementById('cluster-count');
    if (countDisplay) {
      countDisplay.textContent = clusterCount;
    }
  }

  // ============================================================================
  // Main Update Loop
  // ============================================================================
  function update() {
    if (!CONFIG.enabled) return;

    const entities = getGameEntities();
    if (entities.length === 0) return;

    const cameraOffset = getGameCameraOffset();
    const grid = buildSpatialGrid(entities, CONFIG.cellSize);
    const highDensity = identifyHighDensityCells(grid, CONFIG.threshold);

    if (highDensity.length === 0) {
      overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
      return;
    }

    const clusters = mergeAdjacentCells(highDensity);
    renderClusters(clusters, CONFIG.cellSize, cameraOffset);
  }

  // ============================================================================
  // Initialization
  // ============================================================================
  function init() {
    createOverlay();
    createControlPanel();

    // Update loop
    setInterval(() => {
      update();
    }, CONFIG.updateInterval);

    console.log('[Lag Cluster Detector] Initialized');
  }

  // Wait for DOM to be fully ready, then initialize
  const waitForGame = setInterval(() => {
    if (window.game && window.game.entities) {
        clearInterval(waitForGame);
        init();
    }
  }, 200);

})();
