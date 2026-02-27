/** Social sharing: canvas → PNG, optional Imgur upload for embeddable links. */

const IMGUR_CLIENT_ID = '';

function openInBackground(url) {
  const w = window.open(url, '_blank', 'noopener');
  if (w) {
    w.blur();
    window.focus();
  }
}

let headerEl = null;
let getCanvasRef = null;
let getExpertiseAreasRef = null;
let getAnswerCountRef = null;
let getShareDataRef = null;

const SHARE_MIN_ANSWERS = 5;

export function init(headerElement, getCanvas, getExpertiseAreas, getAnswerCount, getShareData) {
  if (!headerElement) return;

  headerEl = headerElement;
  getCanvasRef = getCanvas;
  getExpertiseAreasRef = getExpertiseAreas;
  getAnswerCountRef = getAnswerCount || (() => 0);
  getShareDataRef = getShareData || null;

  const shareBtn = document.getElementById('share-btn');
  if (shareBtn) {
    shareBtn.addEventListener('click', showShareDialog);
  }

  // Backdrop click to close
  const shareModal = document.getElementById('share-modal');
  if (shareModal) {
    shareModal.addEventListener('click', (e) => {
      if (e.target === shareModal) shareModal.hidden = true;
    });
  }
}

function shareImageColor(v) {
  const val = Math.max(0, Math.min(1, v));
  let r, g, b;
  if (val < 0.5) {
    const t = val / 0.5;
    r = Math.round(157 + t * (245 - 157));
    g = Math.round(22 + t * (220 - 22));
    b = Math.round(46 + t * (105 - 46));
  } else {
    const t = (val - 0.5) / 0.5;
    r = Math.round(245 + t * (0 - 245));
    g = Math.round(220 + t * (105 - 220));
    b = Math.round(105 + t * (62 - 105));
  }
  return [r, g, b];
}

function generateShareImage(data) {
  const W = 800;
  const H = 600;
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, W, H);

  const { estimateGrid, articles, answeredQuestions } = data;
  const N = 50;

  // Draw heatmap grid matching the full-map renderer style:
  // bilinear interpolation at higher resolution with proper opacity
  if (estimateGrid && estimateGrid.length === N * N) {
    const CELLS = 100;
    const cellW = W / CELLS;
    const cellH = H / CELLS;

    function sampleGrid(gxf, gyf) {
      const gx0 = Math.max(0, Math.min(N - 1, Math.floor(gxf)));
      const gy0 = Math.max(0, Math.min(N - 1, Math.floor(gyf)));
      const gx1 = Math.min(N - 1, gx0 + 1);
      const gy1 = Math.min(N - 1, gy0 + 1);
      const fx = gxf - gx0;
      const fy = gyf - gy0;
      const v00 = estimateGrid[gy0 * N + gx0];
      const v10 = estimateGrid[gy0 * N + gx1];
      const v01 = estimateGrid[gy1 * N + gx0];
      const v11 = estimateGrid[gy1 * N + gx1];
      const top = v00 + (v10 - v00) * fx;
      const bot = v01 + (v11 - v01) * fx;
      return top + (bot - top) * fy;
    }

    ctx.globalAlpha = 0.45;
    for (let sy = 0; sy < CELLS; sy++) {
      for (let sx = 0; sx < CELLS; sx++) {
        const gxf = ((sx + 0.5) / CELLS) * N - 0.5;
        const gyf = ((sy + 0.5) / CELLS) * N - 0.5;
        const val = sampleGrid(gxf, gyf);
        const [r, g, b] = shareImageColor(val);
        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.fillRect(sx * cellW, sy * cellH, cellW + 0.5, cellH + 0.5);
      }
    }
    ctx.globalAlpha = 1;
  }

  // Draw 50×50 grid lines for spatial reference
  {
    const N = 50;
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.08)';
    ctx.lineWidth = 0.5;
    for (let i = 1; i < N; i++) {
      const x = (i / N) * W;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    for (let i = 1; i < N; i++) {
      const y = (i / N) * H;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }
  }

  // Draw Wikipedia articles as small gray dots (brighter)
  if (articles && articles.length > 0) {
    ctx.fillStyle = 'rgba(148, 163, 184, 0.55)';
    for (const a of articles) {
      ctx.fillRect(a.x * W - 0.75, a.y * H - 0.75, 1.5, 1.5);
    }
  }

  // Draw video markers as subtle small squares
  const { videos } = data;
  if (videos && videos.length > 0) {
    ctx.fillStyle = 'rgba(148, 163, 184, 0.02)';
    for (const v of videos) {
      ctx.fillRect(v.x * W - 0.5, v.y * H - 0.5, 1, 1);
    }
  }

  // Draw answered questions as slightly larger dots with outline
  if (answeredQuestions && answeredQuestions.length > 0) {
    for (const q of answeredQuestions) {
      const px = q.x * W;
      const py = q.y * H;
      ctx.beginPath();
      ctx.arc(px, py, 5, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(px, py, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = q.isSkipped ? '#d4a017' : q.isCorrect ? '#00693e' : '#9d162e';
      ctx.fill();
    }
  }

  // Draw vertical colorbar legend (bottom-right corner)
  {
    const barW = 12;
    const barH = 120;
    const barX = W - barW - 20;
    const barY = H - barH - 30;
    const grad = ctx.createLinearGradient(barX, barY, barX, barY + barH);
    // Top = high knowledge (green), bottom = low knowledge (red)
    const [rH, gH, bH] = shareImageColor(1.0);
    const [rM, gM, bM] = shareImageColor(0.5);
    const [rL, gL, bL] = shareImageColor(0.0);
    grad.addColorStop(0, `rgb(${rH},${gH},${bH})`);
    grad.addColorStop(0.5, `rgb(${rM},${gM},${bM})`);
    grad.addColorStop(1, `rgb(${rL},${gL},${bL})`);

    ctx.fillStyle = grad;
    ctx.fillRect(barX, barY, barW, barH);

    // Border
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)';
    ctx.lineWidth = 0.5;
    ctx.strokeRect(barX, barY, barW, barH);

    // Labels
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText('High', barX - 4, barY + 8);
    ctx.fillText('Low', barX - 4, barY + barH - 2);

    // Title label
    ctx.save();
    ctx.translate(barX - 6, barY + barH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.font = '8px sans-serif';
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillText('Estimated Knowledge', 0, -8);
    ctx.restore();
  }

  return canvas.toDataURL('image/png');
}

export function showShareDialog() {
  const modal = document.getElementById('share-modal');
  if (!modal) return;

  const totalAnswers = getAnswerCountRef ? getAnswerCountRef() : 0;
  const expertiseAreas = getExpertiseAreasRef ? getExpertiseAreasRef() : [];

  if (totalAnswers < SHARE_MIN_ANSWERS || !expertiseAreas || expertiseAreas.length === 0) {
    const contentEl = modal.querySelector('.share-modal-content');
    const teaserUrl = 'https://context-lab.com/mapper';
    const teaserText = 'Check out \u{1F5FA}\uFE0F Knowledge Mapper: an interactive tool that maps out everything you know! Answer questions and watch a personalized map of YOUR knowledge take shape in real time.\n\nhttps://context-lab.com/mapper';
    const remaining = Math.max(0, SHARE_MIN_ANSWERS - totalAnswers);
    const progressNote = totalAnswers > 0 && remaining > 0
      ? `Answer ${remaining} more question${remaining !== 1 ? 's' : ''} to unlock your personalized share with top expertise areas!`
      : totalAnswers > 0
        ? 'Keep answering questions to build up your expertise areas for a personalized share!'
        : 'Select a knowledge domain to explore, and answer a few questions to unlock a shareable personalized map featuring your top areas of expertise.';
    if (contentEl) {
      contentEl.innerHTML = `
        <button type="button" class="modal-close-x close-modal" aria-label="Close" style="position:absolute;top:0.75rem;right:0.75rem;">&times;</button>
        <h2 style="margin-bottom: 1rem; font-family: var(--font-heading); color: var(--color-primary);">Share Knowledge Mapper</h2>
        <p style="line-height: 1.7; margin-bottom: 1.25rem; font-size: 0.9rem;">
          ${teaserText}
        </p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1.25rem;">
          <button type="button" class="share-action-btn" data-action="linkedin" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: #0a66c2; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
            <i class="fa-brands fa-linkedin"></i> LinkedIn
          </button>
          <button type="button" class="share-action-btn" data-action="twitter" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: #000000; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
            <i class="fa-brands fa-x-twitter"></i> X
          </button>
          <button type="button" class="share-action-btn" data-action="bluesky" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: #1185fe; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
            <i class="fa-brands fa-bluesky"></i> Bluesky
          </button>
          <button type="button" class="share-action-btn" data-action="copy" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: var(--color-primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
            <i class="fa-solid fa-copy"></i> Copy
          </button>
        </div>
        <p style="font-size: 0.8rem; color: var(--color-text-muted); text-align: center; font-style: italic;">
          ${progressNote}
        </p>
      `;

      // Wire teaser share actions
      const actionBtns = contentEl.querySelectorAll('.share-action-btn');
      for (const btn of actionBtns) {
        btn.addEventListener('click', () => {
          const action = btn.getAttribute('data-action');
          handleShareAction(action, teaserText, teaserUrl, '');
        });
        btn.addEventListener('mouseover', () => { btn.style.opacity = '0.9'; btn.style.transform = 'scale(1.02)'; });
        btn.addEventListener('mouseout', () => { btn.style.opacity = '1'; btn.style.transform = 'scale(1)'; });
      }

      // Wire X close
      const closeBtn = contentEl.querySelector('.close-modal');
      if (closeBtn) closeBtn.addEventListener('click', () => { modal.hidden = true; });
    }
    modal.hidden = false;
    modal.offsetHeight; // force reflow so opacity transition fires after display:none removal
    return;
  }

  // Get top 3 expertise areas
  const top3 = expertiseAreas.slice(0, 3).map(a => a.label).join(', ');

  let imageDataUrl = '';
  const shareData = getShareDataRef ? getShareDataRef() : null;
  if (shareData) {
    try {
      imageDataUrl = generateShareImage(shareData);
    } catch (err) {
      console.error('[share] Failed to generate share image:', err);
    }
  }
  if (!imageDataUrl) {
    const canvas = getCanvasRef ? getCanvasRef() : null;
    if (canvas) {
      try {
        imageDataUrl = canvas.toDataURL('image/png');
      } catch (err) {
        console.error('[share] Failed to render canvas:', err);
      }
    }
  }

  // Compose share text
  const shareText = `I mapped my knowledge with \u{1F5FA}\uFE0F Knowledge Mapper! My top areas: ${top3}\n\n\nhttps://context-lab.com/mapper`;
  const shareUrl = 'https://context-lab.com/mapper';

  // Populate modal
  const contentEl = modal.querySelector('.share-modal-content');
  if (contentEl) {
    contentEl.innerHTML = `
      <button type="button" class="modal-close-x close-modal" aria-label="Close" style="position:absolute;top:0.75rem;right:0.75rem;">&times;</button>
      <h2 style="margin-bottom: 1.5rem; font-family: var(--font-heading); color: var(--color-primary);">Share Your Knowledge Map</h2>

      ${imageDataUrl ? `
        <div style="margin-bottom: 1.5rem; text-align: center;">
          <img src="${imageDataUrl}" alt="Knowledge map preview" style="max-width: 100%; max-height: 300px; border-radius: 8px; border: 1px solid var(--color-border);">
        </div>
      ` : ''}

      <div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--color-surface-raised); border-radius: 8px;">
        <p style="font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--color-text-muted);">Share text:</p>
        <p style="font-size: 0.95rem; line-height: 1.5; margin: 0; word-break: break-word;">${shareText}</p>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1.5rem;">
        <button class="share-action-btn" data-action="linkedin" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: #0a66c2; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
          <i class="fa-brands fa-linkedin"></i> LinkedIn
        </button>
        <button class="share-action-btn" data-action="twitter" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: #000000; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
          <i class="fa-brands fa-x-twitter"></i> X
        </button>
        <button class="share-action-btn" data-action="bluesky" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: #1185fe; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
          <i class="fa-brands fa-bluesky"></i> Bluesky
        </button>
        <button class="share-action-btn" data-action="copy" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: var(--color-primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
          <i class="fa-solid fa-copy"></i> Copy
        </button>
        ${imageDataUrl ? `
        <button class="share-action-btn" data-action="copy-image" style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: var(--color-secondary); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease;">
          <i class="fa-solid fa-image"></i> Copy Image
        </button>
        ` : ''}
      </div>

      ${imageDataUrl ? `
        ${IMGUR_CLIENT_ID ? `
        <button class="share-action-btn" data-action="imgur" style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: #1bb76e; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease; margin-bottom: 0.75rem;">
          <i class="fa-solid fa-upload"></i> Upload &amp; Get Shareable Link
        </button>
        <div id="imgur-result" style="display:none; margin-bottom: 0.75rem; padding: 0.75rem; background: var(--color-surface-raised); border-radius: 6px; font-size: 0.85rem; word-break: break-all;"></div>
        ` : ''}
        <button class="share-action-btn" data-action="download" style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: var(--color-secondary); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s ease; margin-bottom: 1rem;">
          <i class="fa-solid fa-download"></i> Download Image
        </button>
      ` : ''}

    `;

    // Wire up action buttons
    const actionBtns = contentEl.querySelectorAll('.share-action-btn');
    for (const btn of actionBtns) {
      btn.addEventListener('click', () => {
        const action = btn.getAttribute('data-action');
        handleShareAction(action, shareText, shareUrl, imageDataUrl);
      });
      btn.addEventListener('mouseover', () => {
        btn.style.opacity = '0.9';
        btn.style.transform = 'scale(1.02)';
      });
      btn.addEventListener('mouseout', () => {
        btn.style.opacity = '1';
        btn.style.transform = 'scale(1)';
      });
    }

    // Wire up close button
    const closeBtn = contentEl.querySelector('.close-modal');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        modal.hidden = true;
      });
    }
  }

  modal.hidden = false;
  modal.offsetHeight; // force reflow so opacity transition fires after display:none removal
}

async function handleShareAction(action, shareText, shareUrl, imageDataUrl) {
  if (action === 'linkedin') {
    if (navigator.canShare && imageDataUrl) {
      try {
        const blob = await (await fetch(imageDataUrl)).blob();
        const file = new File([blob], 'knowledge-map.png', { type: 'image/png' });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ text: shareText, url: shareUrl, files: [file] });
          return;
        }
      } catch (e) {
        // fallback to URL sharing
      }
    }
    try { await navigator.clipboard.writeText(shareText); } catch { /* ok */ }
    const btn = document.querySelector('[data-action="linkedin"]');
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Text copied — paste into your post!';
      setTimeout(() => { btn.innerHTML = orig; }, 4000);
    }
    const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;
    openInBackground(linkedinUrl);
  } else if (action === 'twitter') {
    if (navigator.canShare && imageDataUrl) {
      try {
        const blob = await (await fetch(imageDataUrl)).blob();
        const file = new File([blob], 'knowledge-map.png', { type: 'image/png' });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ text: shareText, url: shareUrl, files: [file] });
          return;
        }
      } catch (e) {
        // fallback to URL sharing
      }
    }
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`;
    openInBackground(twitterUrl);
  } else if (action === 'bluesky') {
    if (navigator.canShare && imageDataUrl) {
      try {
        const blob = await (await fetch(imageDataUrl)).blob();
        const file = new File([blob], 'knowledge-map.png', { type: 'image/png' });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ text: shareText, url: shareUrl, files: [file] });
          return;
        }
      } catch (e) {
        // fallback to URL sharing
      }
    }
    const blueskyUrl = `https://bsky.app/intent/compose?text=${encodeURIComponent(shareText)}`;
    openInBackground(blueskyUrl);
  } else if (action === 'copy') {
    navigator.clipboard.writeText(shareText).then(() => {
      const btn = document.querySelector('[data-action="copy"]');
      if (btn) {
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
        setTimeout(() => {
          btn.innerHTML = originalText;
        }, 2000);
      }
    }).catch(err => {
      console.error('[share] Failed to copy:', err);
    });
    if (imageDataUrl) {
      try {
        const blob = await (await fetch(imageDataUrl)).blob();
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      } catch (e) {
        // text copy already succeeded
      }
    }
  } else if (action === 'copy-image') {
    if (imageDataUrl) {
      try {
        const blob = await (await fetch(imageDataUrl)).blob();
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
        const btn = document.querySelector('[data-action="copy-image"]');
        if (btn) {
          const originalText = btn.innerHTML;
          btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
          setTimeout(() => {
            btn.innerHTML = originalText;
          }, 2000);
        }
      } catch (err) {
        console.error('[share] Failed to copy image:', err);
      }
    }
  } else if (action === 'imgur') {
    if (!imageDataUrl || !IMGUR_CLIENT_ID) return;
    const btn = document.querySelector('[data-action="imgur"]');
    const resultEl = document.getElementById('imgur-result');
    if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading…';

    try {
      const base64 = imageDataUrl.split(',')[1];
      const form = new FormData();
      form.append('image', base64);
      form.append('type', 'base64');
      form.append('title', 'Knowledge Mapper');

      const res = await fetch('https://api.imgur.com/3/image', {
        method: 'POST',
        headers: { Authorization: `Client-ID ${IMGUR_CLIENT_ID}` },
        body: form,
      });

      const data = await res.json();
      if (data.success && data.data?.link) {
        const imgUrl = data.data.link;
        if (resultEl) {
          resultEl.style.display = 'block';
          resultEl.innerHTML = `<strong>Image link:</strong> <a href="${imgUrl}" target="_blank" rel="noopener">${imgUrl}</a><br><span style="color:var(--color-text-muted);font-size:0.8rem;">Paste this link in your post to embed the image.</span>`;
        }
        if (btn) btn.innerHTML = '<i class="fa-solid fa-check"></i> Uploaded!';
        try { await navigator.clipboard.writeText(imgUrl); } catch { /* ok */ }
      } else {
        throw new Error(data.data?.error || 'Upload failed');
      }
    } catch (err) {
      console.error('[share] Imgur upload failed:', err);
      if (btn) btn.innerHTML = '<i class="fa-solid fa-times"></i> Upload Failed';
      if (resultEl) {
        resultEl.style.display = 'block';
        resultEl.innerHTML = `<span style="color:var(--color-incorrect);">Upload failed: ${err.message}</span>`;
      }
    }
  } else if (action === 'download') {
    if (imageDataUrl) {
      const link = document.createElement('a');
      link.href = imageDataUrl;
      link.download = `knowledge-map-${new Date().toISOString().slice(0, 10)}.png`;
      link.click();
    }
  }
}
