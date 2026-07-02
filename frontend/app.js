let allJobs = [];
let activeSource = ''; // 当前选中的来源，空字符串表示"所有"

async function loadJobs() {
    const jobList = document.getElementById('jobList');
    jobList.innerHTML = '<p class="loading">正在加载数据...</p>';

    try {
        const response = await fetch('../data/jobs.json?t=' + new Date().getTime());
        allJobs = await response.json();

        document.getElementById('totalCount').textContent = `共 ${allJobs.length} 条信息`;

        // 动态生成来源筛选卡片
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
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    let filtered = allJobs.filter(job => {
        const matchSearch = job.title.toLowerCase().includes(searchTerm) || 
                          job.source.toLowerCase().includes(searchTerm);
        const matchSource = !activeSource || job.source === activeSource;
        return matchSearch && matchSource;
    });
    
    displayJobs(filtered);
}

function displayJobs(jobs) {
    const jobList = document.getElementById('jobList');
    
    if (jobs.length === 0) {
        jobList.innerHTML = '<p class="no-results">没有找到匹配的招聘信息</p>';
        return;
    }
    
    jobList.innerHTML = jobs.map(job => `
        <div class="job-item" onclick="window.open('${job.url}', '_blank')">
            <div class="job-header">
                <div class="job-title">${job.title}</div>
                <div class="job-source">${job.source}</div>
            </div>
            <div class="job-meta">
                <div class="job-date">📅 ${job.date}</div>
                <div class="job-type">${job.type}</div>
            </div>
        </div>
    `).join('');
}

// 页面加载时自动加载数据
window.addEventListener('DOMContentLoaded', loadJobs);
