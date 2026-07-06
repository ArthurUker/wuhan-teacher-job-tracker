let allJobs = [];
let filteredJobs = []; // 过滤后的数据
let activeSource = ''; // 当前选中的来源，空字符串表示"所有"
let isCrawling = false; // 爬虫是否正在运行中（防重复触发）

// 分页状态
let currentPage = 1;
let perPage = 20;

// 视图状态
let currentView = 'card'; // 'card' 或 'list'

// Cloudflare Worker 代理 URL（部署后替换为实际地址）
const TRIGGER_WORKER_URL = 'https://wuhan-teacher-job-tracker.arthuruker.workers.dev';

// Worker 鉴权 Token
// 安全警告：该 token 对所有访问者可见。
// 目前内置速率限制防滥用；Worker 端必须配置 AUTH_TOKEN 环境变量（已设为 Cloudflare Secret）。
const AUTH_TOKEN = 'guorenkang';

/** 刷新数据 - 只从本地加载 jobs.json，不触发爬虫 */
async function loadJobs() {
    if (isCrawling) return;

    const jobList = document.getElementById('jobList');
    jobList.innerHTML = '<p class="loading">正在加载数据...</p>';

    try {
        const response = await fetch('../data/jobs.json?t=' + new Date().getTime());
        allJobs = await response.json();

        document.getElementById('totalCount').textContent = `共 ${allJobs.length} 条信息`;

        renderSourceCards();

        const now = new Date();
        document.getElementById('lastUpdate').textContent =
            `最后更新: ${now.getFullYear()}-${(now.getMonth()+1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        filterJobs();
    } catch (error) {
        jobList.innerHTML = '<p class="no-results">加载数据失败，请确保已运行爬虫脚本生成数据。</p>';
        console.error('加载数据失败:', error);
    }
}

/** 触发爬虫 - 弹出确认框后才执行 */
function requestTriggerCrawl() {
    if (isCrawling) return;
    if (!confirm('确定要重新抓取招聘信息吗？\n\n预计需要 2-5 分钟，期间不可重复触发。')) {
        return;
    }
    triggerCrawlAndRefresh();
}

function renderSourceCards() {
    const container = document.getElementById('sourceCards');
    const sources = [...new Set(allJobs.map(j => j.source))].sort();
    // "所有来源" + 各来源卡片
    let html = '';
    
    // "所有来源" 卡片
    html += `<div class="source-card ${activeSource === '' ? 'active' : ''}" onclick="selectSource('')">✓ 所有来源</div>`;
    
    for (const s of sources) {
        // 统计该来源的数量
        const count = allJobs.filter(j => j.source === s).length;
        html += `<div class="source-card ${activeSource === s ? 'active' : ''}" onclick="selectSource('${s}')">${s} (${count})</div>`;
    }
    container.innerHTML = html;
}

function selectSource(source) {
    activeSource = source;
    // 更新卡片选中状态
    document.querySelectorAll('.source-card').forEach(card => {
        card.classList.toggle('active', card.textContent.includes(source ? source : '所有来源'));
    });
    filterJobs();
}

function filterJobs() {
    filteredJobs = allJobs.filter(job => {
        const matchSource = !activeSource || job.source === activeSource;
        
        // 始终排除高校招聘（高校作为雇主招教员）
        const matchUniv = !isUniversityRecruitment(job.title);
        
        return matchSource && matchUniv;
    });
    
    // 过滤后重置页码
    currentPage = 1;
    displayCurrentPage();
    renderPagination();
}

/**
 * 判断标题是否为高校招聘（高校作为雇主招教员，需排除）
 * 保留：赴高校专项招聘、大学附属学校招聘
 */
function isUniversityRecruitment(title) {
    const keepPatterns = ['赴高校', '附属中学', '附中', '附属学校', '大学附属', '附小'];
    for (const p of keepPatterns) {
        if (title.includes(p)) return false;
    }
    // "大学/学院/高校" 出现在 "招聘" 之前 → 高校是雇主
    const recruitIdx = title.indexOf('招聘');
    if (recruitIdx < 0) return false;
    const prefix = title.substring(0, recruitIdx);
    return ['大学', '学院', '高校'].some(k => prefix.includes(k));
}

/** 根据当前页码和每页条数，显示对应页的数据 */
function displayCurrentPage() {
    const total = filteredJobs.length;
    const totalPages = Math.ceil(total / perPage) || 1;

    // 确保 currentPage 在合法范围内
    if (currentPage < 1) currentPage = 1;
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * perPage;
    const end = start + perPage;
    const pageJobs = filteredJobs.slice(start, end);

    displayJobs(pageJobs);
}

/** 判断是否为微信公众号来源（链接可能过期） */
function isWechatSource(job) {
    return job.source === '微信公众号' || (job.url && job.url.includes('sogou.com'));
}

/** 复制文本到剪贴板 */
async function copyTitle(title) {
    try {
        await navigator.clipboard.writeText(title);
        alert('已复制标题，请在微信中搜索：' + title);
    } catch (e) {
        prompt('请复制以下文字到微信中搜索：', title);
    }
}

function displayJobs(jobs) {
    const jobList = document.getElementById('jobList');
    
    // 设置列表/卡片视图
    if (currentView === 'list') {
        jobList.classList.add('list-view');
    } else {
        jobList.classList.remove('list-view');
    }
    
    if (jobs.length === 0) {
        jobList.innerHTML = '<p class="no-results">没有找到匹配的招聘信息</p>';
        return;
    }
    
    jobList.innerHTML = jobs.map(job => {
        const wechat = isWechatSource(job);
        // 构建日期显示：标题日期 + 发布日期
        let dateHtml = '';
        if (job.title_date && job.publish_time && job.publish_time !== '未知日期') {
            dateHtml = `📅 标题日期: ${job.title_date} | 发布: ${job.publish_time}`;
        } else if (job.title_date) {
            dateHtml = `📅 ${job.title_date}`;
        } else if (job.publish_time && job.publish_time !== '未知日期') {
            dateHtml = `📅 发布: ${job.publish_time}`;
        } else {
            dateHtml = `📅 ${job.date}`;
        }

        // 截止日期：标红加粗
        let deadlineHtml = '';
        if (job.deadline) {
            const style = job.urgent ? 'color:#e74c3c;font-weight:bold;' : 'color:#e67e22;';
            deadlineHtml = `<div class="job-deadline" style="${style}">⏰ 截止: ${job.deadline}</div>`;
        }

        // 公众号名称
        let accountHtml = '';
        if (job.account_name && job.account_name !== '未知公众号') {
            accountHtml = `<div class="job-account" style="font-size:0.8em;color:#999;margin-top:4px;">📢 ${job.account_name}</div>`;
        }

        // 微信公众号链接过期提示（仅非永久链接显示）
        let expiredHint = '';
        if (wechat) {
            const isPermanent = job.url && job.url.includes('mp.weixin.qq.com');
            if (!isPermanent) {
                expiredHint = `<div class="job-expired-hint" style="font-size:0.78em;color:#e67e22;margin-top:4px;display:flex;align-items:center;gap:6px;">
                    ⚠️ 链接可能已失效
                    <button class="copy-btn" onclick="event.stopPropagation();copyTitle('${job.title.replace(/'/g, "\\'")}');" title="复制标题，在微信中搜索文章">📋 复制标题</button>
                </div>`;
            }
            if (!accountHtml && job.account_name) {
                accountHtml = `<div class="job-account" style="font-size:0.8em;color:#999;margin-top:4px;">📢 ${job.account_name}</div>`;
            }
        }

        const viewClass = currentView === 'list' ? ' list-view' : '';
        const clickAction = `onclick="window.open('${job.url}', '_blank')"`;
        const cursorStyle = 'style="cursor:pointer;"';

        return `
        <div class="job-item${viewClass}" ${clickAction} ${cursorStyle}>
            <div class="job-header">
                <div class="job-title">${job.title}</div>
                <div class="job-source">${job.source}${wechat && job.url && !job.url.includes('mp.weixin.qq.com') ? ' <span style="font-size:0.8em;color:#e67e22">[链接可能失效]</span>' : ''}</div>
            </div>
            <div class="job-meta">
                <div class="job-date">${dateHtml}</div>
                <div class="job-type">${job.type}</div>
            </div>
            ${deadlineHtml}
            ${accountHtml}
            ${expiredHint}
        </div>`;
    }).join('');
}

/** 渲染分页导航按钮 */
function renderPagination() {
    const nav = document.getElementById('paginationNav');
    const total = filteredJobs.length;
    const totalPages = Math.ceil(total / perPage) || 1;

    if (totalPages <= 1) {
        nav.innerHTML = `<span class="page-info">共 ${total} 条</span>`;
        return;
    }

    let html = '';

    // 上一页
    html += `<button class="page-btn" onclick="prevPage()" ${currentPage <= 1 ? 'disabled' : ''}>‹ 上一页</button>`;

    // 页码按钮（最多显示7个）
    const maxVisible = 7;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        html += `<button class="page-btn" onclick="goToPage(1)">1</button>`;
        if (startPage > 2) html += `<span class="page-info">...</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += `<span class="page-info">...</span>`;
        html += `<button class="page-btn" onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }

    // 下一页
    html += `<button class="page-btn" onclick="nextPage()" ${currentPage >= totalPages ? 'disabled' : ''}>下一页 ›</button>`;

    // 页码信息
    html += `<span class="page-info">第 ${currentPage}/${totalPages} 页，共 ${total} 条</span>`;

    nav.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    displayCurrentPage();
    renderPagination();
    // 滚动到顶部
    document.getElementById('jobList').scrollIntoView({ behavior: 'smooth' });
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        displayCurrentPage();
        renderPagination();
        document.getElementById('jobList').scrollIntoView({ behavior: 'smooth' });
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredJobs.length / perPage) || 1;
    if (currentPage < totalPages) {
        currentPage++;
        displayCurrentPage();
        renderPagination();
        document.getElementById('jobList').scrollIntoView({ behavior: 'smooth' });
    }
}

function changePerPage() {
    const select = document.getElementById('perPage');
    perPage = parseInt(select.value);
    currentPage = 1;
    displayCurrentPage();
    renderPagination();
}

function switchView(view) {
    currentView = view;
    
    // 更新按钮状态
    document.getElementById('cardViewBtn').classList.toggle('active', view === 'card');
    document.getElementById('listViewBtn').classList.toggle('active', view === 'list');
    
    // 重新显示当前页
    displayCurrentPage();
}

// 页面加载时自动加载数据
window.addEventListener('DOMContentLoaded', loadJobs);


/* ========== 触发 GitHub Actions 爬虫 ========== */

// 轮询状态用的 timer ID
let statusPollTimer = null;

async function triggerCrawlAndRefresh() {
    if (isCrawling) return;
    isCrawling = true;

    const jobList = document.getElementById('jobList');
    const crawlBtn = document.querySelector('button[onclick="requestTriggerCrawl()"]');
    const refreshBtn = document.querySelector('button[onclick="loadJobs()"]');

    jobList.innerHTML = '<p class="loading">⏳ 正在触发爬虫运行...</p>';
    if (crawlBtn) { crawlBtn.disabled = true; }
    if (refreshBtn) { refreshBtn.disabled = true; }

    try {
        // 1. 调用 Worker 代理触发 Actions
        const fetchOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        // 如果配置了 AUTH_TOKEN，添加鉴权头
        if (AUTH_TOKEN) {
            fetchOptions.headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
        }
        
        const resp = await fetch(TRIGGER_WORKER_URL, fetchOptions);
        const result = await resp.json();

        if (!resp.ok && !result.success) {
            throw new Error(result.error || `HTTP ${resp.status}`);
        }

        // 2. 显示等待状态，开始轮询状态和数据的更新
        showWaitingState(result.runUrl);

        // 3. 开始轮询 GitHub Actions 运行状态（每 5 秒）
        startStatusPolling(result.runUrl);

        // 4. 每 15 秒轮询一次数据更新，最多等 5 分钟
        let attempts = 0;
        const maxAttempts = 20; // 20 * 15s = 300s = 5min
        const pollInterval = setInterval(async () => {
            attempts++;
            const statusEl = document.getElementById('crawlStatus');
            if (statusEl && statusEl.dataset.status === 'completed') {
                // 状态已完结，停止轮询数据
                clearInterval(pollInterval);
                return;
            }
            refreshBtn.textContent = `⏳ 爬取中 (${attempts * 15}s)...`;
            if (crawlBtn) crawlBtn.disabled = true;

            try {
                const checkResp = await fetch('../data/jobs.json?t=' + Date.now());
                if (checkResp.ok) {
                    const newJobs = await checkResp.json();
                    if (newJobs.length !== allJobs.length || JSON.stringify(newJobs) !== JSON.stringify(allJobs)) {
                        clearInterval(pollInterval);
                        allJobs = [];
                        await loadFreshData();
                        return;
                    }
                }
            } catch (e) { /* 忽略 */ }

            if (attempts >= maxAttempts) {
                clearInterval(pollInterval);
                jobList.innerHTML += `
                    <p style="text-align:center;color:#e67e22;padding:10px;">
                        ⏱ 爬虫仍在运行中，请稍后手动刷新页面查看最新数据。
                        <br><a href="${result.runUrl || '#'}" target="_blank" style="color:#667eea;">查看运行状态 →</a>
                    </p>`;
                resetRefreshBtn();
            }
        }, 15000);

        // 先立即加载一次当前数据
        await loadFreshData();

    } catch (err) {
        jobList.innerHTML = `<p class="no-results">
            ❌ 触发爬虫失败: ${err.message}<br>
            <span style="font-size:0.85em;color:#999;">提示：请确认已部署 Cloudflare Worker 代理</span>
        </p>`;
        resetRefreshBtn();
    }
}

async function loadFreshData() {
    const jobList = document.getElementById('jobList');
    try {
        const response = await fetch('../data/jobs.json?t=' + Date.now());
        allJobs = await response.json();
        document.getElementById('totalCount').textContent = `共 ${allJobs.length} 条信息`;
        renderSourceCards();
        const now = new Date();
        document.getElementById('lastUpdate').textContent =
            `最后更新: ${now.getFullYear()}-${(now.getMonth()+1).toString().padStart(2,'0')}-${now.getDate().toString().padStart(2,'0')} ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
        filterJobs();
        // 数据加载完成，恢复按钮
        if (isCrawling) {
            const statusEl = document.getElementById('crawlStatus');
            if (statusEl) statusEl.textContent = '✅ 数据已更新！';
            resetRefreshBtn();
        }
    } catch (error) {
        jobList.innerHTML = '<p class="no-results">加载数据失败</p>';
    }
}

function showWaitingState(runUrl) {
    const jobList = document.getElementById('jobList');
    jobList.innerHTML = `
        <div class="waiting-status" id="waitingStatus">
            <div class="spinner"></div>
            <h3>🚀 爬虫已触发，正在抓取最新招聘信息...</h3>
            <p>预计需要 2-5 分钟，页面将自动刷新</p>
            <div id="crawlStatus" style="margin:10px 0;font-weight:bold;color:#f39c12;">
                ⏳ 爬虫运行中...
            </div>
            ${runUrl ? `<a href="${runUrl}" target="_blank" style="color:#667eea;">📋 查看运行日志 →</a>` : ''}
            <div class="poll-progress" id="pollProgress"></div>
        </div>`;
}

/** 轮询 GitHub Actions 运行状态，每 5 秒查询一次 */
function startStatusPolling(runUrl) {
    if (statusPollTimer) {
        clearInterval(statusPollTimer);
    }

    statusPollTimer = setInterval(async () => {
        try {
            const fetchOptions = {};
            if (AUTH_TOKEN) {
                fetchOptions.headers = { 'Authorization': `Bearer ${AUTH_TOKEN}` };
            }

            const resp = await fetch(TRIGGER_WORKER_URL, fetchOptions);
            if (!resp.ok) return;

            const result = await resp.json();
            const statusEl = document.getElementById('crawlStatus');
            if (!statusEl) return;

            statusEl.dataset.status = result.status || '';

            if (result.status === 'in_progress' || result.status === 'queued') {
                const start = result.createdAt ? new Date(result.createdAt) : new Date();
                const elapsed = Math.round((Date.now() - start.getTime()) / 1000);
                statusEl.textContent = `⏳ 爬虫运行中...（已运行 ${elapsed}s）`;
                statusEl.style.color = '#f39c12';
            } else if (result.status === 'completed') {
                clearInterval(statusPollTimer);
                statusPollTimer = null;

                if (result.conclusion === 'success') {
                    statusEl.textContent = '✅ 爬虫运行成功！正在刷新数据...';
                    statusEl.style.color = '#27ae60';
                } else {
                    statusEl.textContent = `❌ 爬虫运行失败: ${result.conclusion}`;
                    statusEl.style.color = '#e74c3c';
                    resetRefreshBtn();
                }
            }
        } catch (e) { /* 忽略轮询错误 */ }
    }, 5000);
}

function resetRefreshBtn() {
    isCrawling = false;
    const crawlBtn = document.querySelector('button[onclick="requestTriggerCrawl()"]');
    const btn = document.querySelector('button[onclick="loadJobs()"]');
    if (crawlBtn) {
        crawlBtn.disabled = false;
        crawlBtn.textContent = '🚀 重新抓取';
    }
    if (btn) {
        btn.disabled = false;
        btn.textContent = '🔄 刷新数据';
    }
}
