let allJobs = [];

async function loadJobs() {
    const jobList = document.getElementById('jobList');
    jobList.innerHTML = '<p class="loading">正在加载数据...</p>';

    try {
        const response = await fetch('../data/jobs.json?t=' + new Date().getTime());
        allJobs = await response.json();

        document.getElementById('totalCount').textContent = `共 ${allJobs.length} 条信息`;

        // 动态生成数据源下拉选项
        const sourceFilter = document.getElementById('sourceFilter');
        const currentVal = sourceFilter.value;
        const sources = [...new Set(allJobs.map(j => j.source))].sort();
        sourceFilter.innerHTML = '<option value="">所有来源</option>';
        for (const s of sources) {
            const opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s;
            if (s === currentVal) opt.selected = true;
            sourceFilter.appendChild(opt);
        }

        const now = new Date();
        document.getElementById('lastUpdate').textContent =
            `最后更新: ${now.getFullYear()}-${(now.getMonth()+1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        filterJobs();
    } catch (error) {
        jobList.innerHTML = '<p class="no-results">加载数据失败，请确保已运行爬虫脚本生成数据。</p>';
        console.error('加载数据失败:', error);
    }
}

function filterJobs() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const sourceFilter = document.getElementById('sourceFilter').value;
    
    let filtered = allJobs.filter(job => {
        const matchSearch = job.title.toLowerCase().includes(searchTerm) || 
                          job.source.toLowerCase().includes(searchTerm);
        const matchSource = !sourceFilter || job.source === sourceFilter;
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
