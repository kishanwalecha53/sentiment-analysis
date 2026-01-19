let rawData = null;
let originalDimensionSummaries = null;
let tempDimensionSummaries = null;
let filteredReviewsData = null;
let selectedSentiment = 'positive';
let selectedDimension = 'Service Quality';
let isFilterActive = false;
const dimensions = ['Service Quality', 'Facility Experience', 'Trust & Safety', 'Clinical Care', 'Operations'];

// Cache management with expiration
const CACHE_DURATION = 12 * 60 * 60 * 1000; // 12 hours in milliseconds

function setCacheWithExpiry(key, value) {
  const item = {
    value: value,
    expiry: Date.now() + CACHE_DURATION
  };
  localStorage.setItem(key, JSON.stringify(item));
}

function getCacheWithExpiry(key) {
  const itemStr = localStorage.getItem(key);
  
  if (!itemStr) {
    return null;
  }
  
  try {
    const item = JSON.parse(itemStr);
    
    // Check if expired
    if (Date.now() > item.expiry) {
      localStorage.removeItem(key);
      return null;
    }
    
    return item.value;
  } catch (e) {
    localStorage.removeItem(key);
    return null;
  }
}

function clearExpiredCache() {
  // Clear all expired cache entries on page load
  const keys = Object.keys(localStorage);
  keys.forEach(key => {
    if (key.startsWith('filter_')) {
      getCacheWithExpiry(key); // This will remove if expired
    }
  });
}

// Clear expired cache on page load
clearExpiredCache();

// Load data
fetch('./analysis_results.json')
  .then(r => r.json())
  .then(json => { 
    rawData = json; 
    originalDimensionSummaries = json.dimension_summaries;
    initFromData(json); 
    initializeFilters();
  });

function initFromData(data) {
  rawData = data;
  document.getElementById('totalReviews').innerText = data.metadata?.total_reviews ?? '—';
  
  const sd = data.summary_statistics?.sentiment_distribution?.counts || {};
  const sp = data.summary_statistics?.sentiment_distribution?.percentages || {};
  document.getElementById('count-positive').innerText = sd.positive ?? 0;
  document.getElementById('count-negative').innerText = sd.negative ?? 0;
  document.getElementById('count-neutral').innerText = sd.neutral ?? 0;
  document.getElementById('count-doubtful').innerText = sd.doubtful ?? 0;
  document.getElementById('pct-positive').innerText = (sp.positive ? sp.positive.toFixed(2) + '%' : '');
  document.getElementById('pct-negative').innerText = (sp.negative ? sp.negative.toFixed(2) + '%' : '');
  document.getElementById('pct-neutral').innerText = (sp.neutral ? sp.neutral.toFixed(2) + '%' : '');
  document.getElementById('pct-doubtful').innerText = (sp.doubtful ? sp.doubtful.toFixed(2) + '%' : '');
  
  updateOverallSummary();

  const tt = data.summary_statistics?.top_themes || [];
  const tnode = document.getElementById('topThemes'); 
  tnode.innerHTML = '';
  tt.slice(0, 5).forEach(t => {
    const div = document.createElement('div');
    div.className = 'theme-item';
    div.innerHTML = `<span>${t[0]}</span><span>(${t[1]})</span>`;
    tnode.appendChild(div);
  });

  renderDimensionButtons();
  buildCharts(data);
  
  document.querySelectorAll('.sentiment-card').forEach(el => 
    el.addEventListener('click', () => {
      selectedSentiment = el.dataset.sentiment;
      document.getElementById('selectedSentiment').innerText = capitalize(selectedSentiment);
      updateOverallSummary();
      document.querySelectorAll('.sentiment-card').forEach(p => p.classList.remove('active'));
      el.classList.add('active');
      refreshInsights();
      renderDimensionButtons();
    })
  );
  
  document.getElementById('selectedDimension').innerText = selectedDimension;
  document.getElementById('selectedSentiment').innerText = capitalize(selectedSentiment);
  refreshInsights();
}

function showFullscreenLoader() {
  let loader = document.getElementById('fullscreenLoader');
  if (!loader) {
    loader = document.createElement('div');
    loader.id = 'fullscreenLoader';
    loader.className = 'fullscreen-loader';
    loader.innerHTML = '<div class="fullscreen-spinner"></div>';
    document.body.appendChild(loader);
  }
  loader.classList.add('active');
  // Disable all buttons
  document.querySelectorAll('button').forEach(btn => btn.disabled = true);
}

function hideFullscreenLoader() {
  const loader = document.getElementById('fullscreenLoader');
  if (loader) {
    loader.classList.remove('active');
    // Re-enable all buttons
    document.querySelectorAll('button').forEach(btn => btn.disabled = false);
  }
}

// Filter functionality
function initializeFilters() {
  const applyBtn = document.getElementById('applyFilter');
  const clearBtn = document.getElementById('clearFilter');
  const monthFilter = document.getElementById('monthFilter');
  const startDate = document.getElementById('startDate');
  const endDate = document.getElementById('endDate');
  const clearCacheBtn = document.getElementById('clearCache');
  if (clearCacheBtn) {
    clearCacheBtn.addEventListener('click', () => {
      const keys = Object.keys(localStorage);
      let count = 0;
      keys.forEach(key => {
        if (key.startsWith('filter_')) {
          localStorage.removeItem(key);
          count++;
        }
      });
      alert(`Cleared ${count} cached filter result(s)`);
    });
  }
  // Set default end date to today
  endDate.valueAsDate = new Date();
  
  // Quick filter selection
  // Quick filter selection
monthFilter.addEventListener('change', (e) => {
  const value = e.target.value;
  const today = new Date();
  let start = new Date();
  
  switch(value) {
    case 'last30':
      start.setDate(today.getDate() - 30);
      startDate.valueAsDate = start;
      endDate.valueAsDate = today;
      break;
      
    case 'last6months':
      start.setMonth(today.getMonth() - 6);
      startDate.valueAsDate = start;
      endDate.valueAsDate = today;
      break;
      
    case 'lastyear':
      start.setFullYear(today.getFullYear() - 1);
      startDate.valueAsDate = start;
      endDate.valueAsDate = today;
      break;
      
    case '2024':
      startDate.value = '2024-01-01';
      endDate.value = '2024-12-31';
      break;
      
    case '2023':
      startDate.value = '2023-01-01';
      endDate.value = '2023-12-31';
      break;
      
    case '2022':
      startDate.value = '2022-01-01';
      endDate.value = '2022-12-31';
      break;
      
    case '2021':
      startDate.value = '2021-01-01';
      endDate.value = '2021-12-31';
      break;
      
    case '2020':
      startDate.value = '2020-01-01';
      endDate.value = '2020-12-31';
      break;
      
    case '2015-2019':
      startDate.value = '2015-01-01';
      endDate.value = '2019-12-31';
      break;
      
    case '2010-2014':
      startDate.value = '2010-01-01';
      endDate.value = '2014-12-31';
      break;
      
    default:
      return;
  }
});
  
  // Apply filter
  applyBtn.addEventListener('click', async () => {
    const start = startDate.value;
    const end = endDate.value;
    
    if (!start || !end) {
      alert('Please select both start and end dates');
      return;
    }
    
    if (new Date(start) > new Date(end)) {
      alert('Start date must be before end date');
      return;
    }
    
    await applyDateFilter(start, end);
  });
  
  // Clear filter
  clearBtn.addEventListener('click', () => {
    clearDateFilter();
  });
}

async function applyDateFilter(startDate, endDate) {
  const loading = document.getElementById('filterLoading');
  const applyBtn = document.getElementById('applyFilter');
  const status = document.getElementById('filterStatus');
  
  try {
    const loaderShownAt = Date.now();
    showFullscreenLoader();
    // Force paint before heavy work starts so overlay is visible
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    loading.style.display = 'flex';
    applyBtn.disabled = true;
    
    // Filter reviews by date
    const filtered = rawData.analyzed_reviews.filter(review => {
      const reviewDateStr = review.date;
      if (!reviewDateStr) return false;
      
      const reviewDate = new Date(reviewDateStr);
      const start = new Date(startDate);
      const end = new Date(endDate);
      end.setHours(23, 59, 59, 999);
      
      return reviewDate >= start && reviewDate <= end;
    });
    
    console.log(`Filtered ${filtered.length} reviews from ${rawData.analyzed_reviews.length} total`);
    
    if (filtered.length === 0) {
      alert('No reviews found in selected date range');
      loading.style.display = 'none';
      applyBtn.disabled = false;
      return;
    }
    
    // STORE FILTERED REVIEWS GLOBALLY
    filteredReviewsData = filtered;
    
    // Check cache first
    const cacheKey = `filter_${startDate}_${endDate}`;
    const cached = getCacheWithExpiry(cacheKey); 
    
    if (cached) {
      console.log('Using cached dimension summaries');
      tempDimensionSummaries = cached;
    } else {
      console.log('Calling API to generate summaries...');
      const controller = new AbortController();
      const timeoutMs = 90000; // 90 seconds
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      let response;
      try {
        response = await fetch('https://psmmc-back.vercel.app/api/generate_summaries', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            reviews: filtered
          }),
          signal: controller.signal
        });
      } catch (err) {
        clearTimeout(timeoutId);
        if (err && err.name === 'AbortError') {
          throw new Error('Request timed out after 90 seconds');
        }
        throw err;
      }
      clearTimeout(timeoutId);
      
      console.log('Response status:', response.status);
      
      const responseText = await response.text();
      
      if (!response.ok) {
        let errorMsg = 'Failed to generate summaries';
        try {
          const errorData = JSON.parse(responseText);
          errorMsg = errorData.error || errorMsg;
        } catch (e) {
          errorMsg = `Server error: ${response.status}`;
        }
        throw new Error(errorMsg);
      }
      
      tempDimensionSummaries = JSON.parse(responseText);
      setCacheWithExpiry(cacheKey, tempDimensionSummaries);
      console.log('Summaries generated and cached in localStorage for 12 hours');
    }
    
    // Update UI
    isFilterActive = true;
    status.innerText = `Showing ${filtered.length} reviews from ${startDate} to ${endDate}`;
    status.classList.add('active');
    
    // UPDATE ALL COUNTS AND DISPLAYS
    updateSentimentCounts();
    buildCharts(rawData);
    renderDimensionButtons();
    refreshInsights();
    
  } catch (error) {
    console.error('Filter error:', error);
    alert(`Error applying filter: ${error.message}`);
  } finally {
    // Keep loader visible for at least 600ms to avoid flashing
    const elapsed = Date.now() - (typeof loaderShownAt !== 'undefined' ? loaderShownAt : Date.now());
    if (elapsed < 600) {
      await new Promise(r => setTimeout(r, 600 - elapsed));
    }
    hideFullscreenLoader();
    loading.style.display = 'none';
    applyBtn.disabled = false;
  }
}

function clearDateFilter() {
  tempDimensionSummaries = null;
  filteredReviewsData = null; // RESET FILTERED REVIEWS
  isFilterActive = false;
  
  const status = document.getElementById('filterStatus');
  const startDate = document.getElementById('startDate');
  const endDate = document.getElementById('endDate');
  const monthFilter = document.getElementById('monthFilter');
  
  status.innerText = '';
  status.classList.remove('active');
  startDate.value = '';
  endDate.valueAsDate = new Date();
  monthFilter.value = '';
  
  // RESTORE ORIGINAL COUNTS AND DISPLAYS
  updateSentimentCounts();
  buildCharts(rawData);
  renderDimensionButtons();
  refreshInsights();
}

// Get current dimension summaries (filtered or original)
function getCurrentDimensionSummaries() {
  return isFilterActive && tempDimensionSummaries ? tempDimensionSummaries : originalDimensionSummaries;
}

function getDimensionCounts(sentiment) {
  const reviews = getCurrentReviews(); // Use current filtered or all reviews
  const counts = {};
  
  (dimensions || []).forEach(dim => {
    counts[dim] = reviews.filter(r => {
      const sentimentMatch = r.analysis?.sentiment === sentiment;
      const hasDimension = r.analysis?.dimensions?.some(d => d.name === dim);
      return sentimentMatch && hasDimension;
    }).length;
  });
  
  return counts;
}

function renderDimensionButtons() {
  const db = document.getElementById('dimensionButtons'); 
  db.innerHTML = '';
  const dimensionCounts = getDimensionCounts(selectedSentiment);

  dimensions.forEach(dim => {
    const btn = document.createElement('button');
    btn.className = 'dim-btn' + (dim === selectedDimension ? ' active' : '');
    btn.innerHTML = `${dim} <span style="font-size: 16px;">(${dimensionCounts[dim]})</span>`;
    
    btn.onclick = () => {
      selectedDimension = dim;
      document.querySelectorAll('.dim-btn').forEach(x => x.classList.remove('active'));
      btn.classList.add('active');
      refreshInsights();
    };
    
    db.appendChild(btn);
  });
}
// Get current reviews based on filter state
function getCurrentReviews() {
  return isFilterActive && filteredReviewsData ? filteredReviewsData : rawData.analyzed_reviews;
}

// Update sentiment card counts based on current reviews
function updateSentimentCounts() {
  const reviews = getCurrentReviews();
  const counts = {
    positive: 0,
    negative: 0,
    neutral: 0,
    doubtful: 0
  };
  
  reviews.forEach(review => {
    const sentiment = review.analysis?.sentiment;
    if (sentiment && counts.hasOwnProperty(sentiment)) {
      counts[sentiment]++;
    }
  });
  
  const total = reviews.length;
  
  // Update counts
  document.getElementById('count-positive').innerText = counts.positive;
  document.getElementById('count-negative').innerText = counts.negative;
  document.getElementById('count-neutral').innerText = counts.neutral;
  document.getElementById('count-doubtful').innerText = counts.doubtful;
  
  // Update percentages
  document.getElementById('pct-positive').innerText = total > 0 ? ((counts.positive / total) * 100).toFixed(2) + '%' : '0%';
  document.getElementById('pct-negative').innerText = total > 0 ? ((counts.negative / total) * 100).toFixed(2) + '%' : '0%';
  document.getElementById('pct-neutral').innerText = total > 0 ? ((counts.neutral / total) * 100).toFixed(2) + '%' : '0%';
  document.getElementById('pct-doubtful').innerText = total > 0 ? ((counts.doubtful / total) * 100).toFixed(2) + '%' : '0%';
}



function updateOverallSummary() {
  const summ = rawData.sentiment_summaries?.[selectedSentiment];
  const ul = document.getElementById('overallSummary'); 
  ul.innerHTML = '';
  if (summ?.key_insights) {
    summ.key_insights.forEach(k => {
      const li = document.createElement('li');
      li.innerText = k;
      ul.appendChild(li);
    });
  } else if (summ?.summary) {
    const li = document.createElement('li');
    li.innerText = summ.summary;
    ul.appendChild(li);
  }
}

function refreshInsights() {
  if (!rawData) return;
  
  const currentSummaries = getCurrentDimensionSummaries();
  const dsumm = currentSummaries?.[selectedDimension];
  const sentBlock = dsumm?.[selectedSentiment] ?? {};
  
  document.getElementById('selectedDimension').innerText = selectedDimension;
  document.getElementById('selectedSentiment').innerText = capitalize(selectedSentiment);

  const insightsSection = document.querySelector('.insights-section');
  const reviewsContainer = document.querySelector('.reviews-container');
  const contentGrid = document.querySelector('.content-grid');
  const overallSummarySection = document.querySelector('.overall-summary');

  if (selectedSentiment === 'neutral' || selectedSentiment === 'doubtful') {
    insightsSection.style.display = 'none';
    overallSummarySection.style.visibility = 'hidden';
    overallSummarySection.style.display = 'block';
    contentGrid.style.gridTemplateColumns = '1fr';
    reviewsContainer.style.width = '100%';
  } else {
    insightsSection.style.display = 'block';
    overallSummarySection.style.visibility = 'visible';
    overallSummarySection.style.display = 'block';
    contentGrid.style.gridTemplateColumns = '1fr 660px';
    reviewsContainer.style.width = 'auto';
  }
  
  document.getElementById('dimensionSummary').innerText = sentBlock.summary || '—';

  const ki = document.getElementById('keyInsights'); 
  ki.innerHTML = '';
  (sentBlock.key_insights || []).forEach(k => {
    const li = document.createElement('li');
    li.innerText = k;
    ki.appendChild(li);
  });

  const rc = document.getElementById('recs'); 
  rc.innerHTML = '';
  (sentBlock.recommendations || []).forEach(k => {
    const li = document.createElement('li');
    li.innerText = k;
    rc.appendChild(li);
  });

  // USE FILTERED REVIEWS HERE
  const currentReviews = getCurrentReviews();
  const reviews = currentReviews.filter(r => {
    if (selectedSentiment === 'doubtful' || selectedSentiment === 'neutral') {
      return r.analysis?.sentiment === selectedSentiment && 
             r.analysis?.dimensions?.some(d => d.name === selectedDimension);
    }
    return r.analysis?.dimensions?.some(d => d.name === selectedDimension && d.sentiment === selectedSentiment);
  });

  const reviewContainer = document.getElementById('reviewsList');
  reviewContainer.innerHTML = '';

  if (reviews.length === 0) {
    reviewContainer.innerHTML = '<div style="color:var(--muted);text-align:center;padding:20px">No reviews found.</div>';
    return;
  }

  reviews.slice(0, 50).forEach(rv => {
    const div = document.createElement('div');
    div.className = 'review-item';

    let reviewContent = `
      <div class="review-header">
        <div class="review-author">${escapeHtml(rv.author || 'Anonymous')}</div>
        <div class="review-rating">${rv.rating || ''} ★</div>
      </div>
      <div class="review-text">${rv.text ? escapeHtml(rv.text) : '<em style="color:#999">(no text)</em>'}</div>
      <div class="review-date">${formatDate(rv.date)}</div>
    `;

    const images = rv.images || [];
    if (images && images.length > 0) {
      reviewContent += `
        <div style="margin-top: 12px;">
          <strong style="font-size: 12px; color: #666;">Attached Images (${images.length}):</strong>
          <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px;">
      `;

      images.forEach((imageUrl, index) => {
        reviewContent += `
          <div style="position: relative; cursor: pointer;">
            <img src="${imageUrl}" 
                 style="width: 80px; height: 80px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0; transition: transform 0.2s;" 
                 alt="Review image ${index + 1}"
                 onmouseover="this.style.transform='scale(1.05)'"
                 onmouseout="this.style.transform='scale(1)'"
                 onclick="showImageModal('${imageUrl}')"
                 onerror="this.parentElement.innerHTML='<div style=\\'width: 80px; height: 80px; background: #f3f4f6; border: 1px solid #e2e8f0; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #9ca3af;\\'>Image unavailable</div>'">
          </div>
        `;
      });

      reviewContent += `
          </div>
        </div>
      `;
    }

    const keyInsights = rv.analysis?.key_insights || [];
    if (keyInsights && keyInsights.length > 0) {
      reviewContent += `
        <div style="margin-top: 12px;">
          <strong style="font-size: 12px; color: #666;">Key Insights:</strong>
          <ul style="margin: 4px 0 0 0; padding-left: 16px; font-size: 12px; color: #374151;">
      `;

      keyInsights.forEach(insight => {
        reviewContent += `<li>${escapeHtml(insight)}</li>`;
      });

      reviewContent += `
          </ul>
        </div>
      `;
    }

    div.innerHTML = reviewContent;
    reviewContainer.appendChild(div);
  });
}

function buildCharts(data) {
  // BAR CHART - Uses current filtered reviews or all reviews
  const currentReviews = getCurrentReviews();
  
  const dims = data.summary_statistics?.top_dimensions || [];
  const labels = dims.map(d => d[0]);
  const countsPerSent = { positive: [], negative: [], neutral: [], doubtful: [] };
  
  labels.forEach(l => {
    const arr = currentReviews.filter(r =>
      r.analysis?.dimensions?.some(d => d.name === l)
    );
    countsPerSent.positive.push(arr.filter(r => r.analysis?.sentiment === 'positive').length);
    countsPerSent.negative.push(arr.filter(r => r.analysis?.sentiment === 'negative').length);
    countsPerSent.neutral.push(arr.filter(r => r.analysis?.sentiment === 'neutral').length);
    countsPerSent.doubtful.push(arr.filter(r => r.analysis?.sentiment === 'doubtful').length);
  });
  
  const barCtx = document.getElementById('barChart').getContext('2d');
  if (window._barChart) window._barChart.destroy();
  window._barChart = new Chart(barCtx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Positive', data: countsPerSent.positive, backgroundColor: '#10b981' },
        { label: 'Negative', data: countsPerSent.negative, backgroundColor: '#ef4444' },
        { label: 'Neutral', data: countsPerSent.neutral, backgroundColor: '#6b7280' },
        { label: 'Doubtful', data: countsPerSent.doubtful, backgroundColor: '#f59e0b' }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      aspectRatio: 2.2,
      plugins: { 
        legend: { position: 'bottom' },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      },
      scales: {
        x: { stacked: false },
        y: { stacked: false, beginAtZero: true }
      }
    }
  });

  // PIE CHART - Always uses original data (never updates with filter)
  const sdist = data.summary_statistics?.sentiment_distribution?.counts || {};
  const pieCtx = document.getElementById('pieChart').getContext('2d');
  if (window._pieChart) window._pieChart.destroy();
  window._pieChart = new Chart(pieCtx, {
    type: 'doughnut',
    data: {
      labels: ['Positive', 'Negative', 'Neutral', 'Doubtful'],
      datasets: [{
        data: [sdist.positive || 0, sdist.negative || 0, sdist.neutral || 0, sdist.doubtful || 0],
        backgroundColor: ['#10b981', '#ef4444', '#6b7280', '#f59e0b']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'right' } }
    }
  });
}

function capitalize(s) {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}
function formatDate(dateString) {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    
    // Check if valid date
    if (isNaN(date.getTime())) return dateString;
    
    // Format: "September 4, 2025"
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
    
    // Alternative shorter format: "Sep 4, 2025"
    // const options = { year: 'numeric', month: 'short', day: 'numeric' };
    // return date.toLocaleDateString('en-US', options);
    
    // Alternative format: "04/09/2025" (DD/MM/YYYY)
    // const day = String(date.getDate()).padStart(2, '0');
    // const month = String(date.getMonth() + 1).padStart(2, '0');
    // const year = date.getFullYear();
    // return `${day}/${month}/${year}`;
    
  } catch (error) {
    return dateString;
  }
}

function escapeHtml(t) {
  return ('' + t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#39;' }[c]));
}

function showImageModal(imageUrl) {
  const modal = document.createElement('div');
  modal.style.position = 'fixed';
  modal.style.top = '0';
  modal.style.left = '0';
  modal.style.width = '100%';
  modal.style.height = '100%';
  modal.style.backgroundColor = 'rgba(0,0,0,0.8)';
  modal.style.display = 'flex';
  modal.style.alignItems = 'center';
  modal.style.justifyContent = 'center';
  modal.style.zIndex = '1000';
  modal.style.cursor = 'pointer';
  
  const fullImg = document.createElement('img');
  fullImg.src = imageUrl;
  fullImg.style.maxWidth = '90%';
  fullImg.style.maxHeight = '90%';
  fullImg.style.borderRadius = '8px';
  fullImg.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
  
  modal.appendChild(fullImg);
  document.body.appendChild(modal);
  
  modal.onclick = () => {
    document.body.removeChild(modal);
  };
}