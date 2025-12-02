// Trading Dashboard JavaScript

const API_BASE = window.location.origin;
let currentAccountId = '11060034';
let charts = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeNavigation();
    initializeAccountSelector();
    initializeBacktestForm();
    loadOverview();
    loadLeaderboard();
    
    // Set default dates for backtest (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    document.getElementById('backtest-end-date').valueAsDate = today;
    document.getElementById('backtest-start-date').valueAsDate = thirtyDaysAgo;
});

// Navigation
function initializeNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Update active state
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding section
            const view = this.dataset.view;
            showSection(view);
        });
    });
}

function showSection(sectionName) {
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => section.classList.remove('active'));
    
    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.classList.add('active');
        
        // Load data for the section
        switch(sectionName) {
            case 'overview':
                loadOverview();
                break;
            case 'leaderboard':
                loadLeaderboard();
                break;
            case 'my-stats':
                loadMyStats();
                break;
            case 'backtests':
                loadBacktests();
                break;
            case 'trades':
                loadTrades();
                break;
        }
    }
}

// Account Selector
function initializeAccountSelector() {
    const accountInput = document.getElementById('accountId');
    const loadButton = document.getElementById('loadAccount');
    
    loadButton.addEventListener('click', function() {
        const accountId = accountInput.value.trim();
        if (accountId) {
            currentAccountId = accountId;
            loadMyStats();
            showNotification('Account loaded: ' + accountId, 'success');
        }
    });
    
    // Load on enter
    accountInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loadButton.click();
        }
    });
}

// API Calls
async function apiGet(endpoint) {
    try {
        const response = await fetch(`${API_BASE}/api/${endpoint}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API Error:', error);
        showNotification('Failed to load data', 'error');
        return null;
    }
}

// Overview Section
async function loadOverview() {
    const data = await apiGet('overview');
    if (data && data.status === 'success') {
        const overview = data.data;
        
        document.getElementById('total-traders').textContent = overview.total_traders || 0;
        document.getElementById('total-trades').textContent = formatNumber(overview.total_trades || 0);
        document.getElementById('total-profit').textContent = formatCurrency(overview.total_profit || 0);
        document.getElementById('avg-win-rate').textContent = formatPercent(overview.avg_win_rate || 0);
    }
    
    // Load top performers preview
    const leaderboardData = await apiGet('leaderboard?limit=5');
    if (leaderboardData && leaderboardData.status === 'success') {
        displayTopPerformersPreview(leaderboardData.data);
    }
}

function displayTopPerformersPreview(traders) {
    const container = document.getElementById('top-performers-preview');
    
    if (!traders || traders.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No traders yet</p></div>';
        return;
    }
    
    let html = '<div class="stats-grid">';
    traders.slice(0, 5).forEach(trader => {
        html += `
            <div class="stat-card">
                <div class="stat-icon">🏅</div>
                <div class="stat-content">
                    <span class="stat-label">${trader.display_name}</span>
                    <span class="stat-value ${trader.total_profit >= 0 ? 'profit-positive' : 'profit-negative'}">
                        ${formatCurrency(trader.total_profit)}
                    </span>
                    <span class="stat-change">${formatPercent(trader.win_rate)} Win Rate</span>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

// Leaderboard Section
async function loadLeaderboard() {
    const metric = document.getElementById('leaderboard-metric')?.value || 'profit';
    const data = await apiGet(`leaderboard?metric=${metric}&limit=50`);
    
    if (data && data.status === 'success') {
        displayLeaderboard(data.data);
    }
}

function displayLeaderboard(traders) {
    const tbody = document.getElementById('leaderboard-body');
    
    if (!traders || traders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><p>No traders yet</p></td></tr>';
        return;
    }
    
    let html = '';
    traders.forEach(trader => {
        const rankClass = trader.rank <= 3 ? `rank-${trader.rank}` : 'rank-default';
        const profitClass = trader.total_profit >= 0 ? 'profit-positive' : 'profit-negative';
        
        html += `
            <tr>
                <td><div class="rank-badge ${rankClass}">${trader.rank}</div></td>
                <td><strong>${trader.display_name}</strong></td>
                <td class="${profitClass}">${formatCurrency(trader.total_profit)}</td>
                <td>${formatPercent(trader.win_rate)}</td>
                <td>${trader.profit_factor ? trader.profit_factor.toFixed(2) : 'N/A'}</td>
                <td>${trader.total_trades}</td>
                <td class="${trader.roi >= 0 ? 'profit-positive' : 'profit-negative'}">
                    ${trader.roi ? formatPercent(trader.roi) : 'N/A'}
                </td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

// Initialize leaderboard controls
document.getElementById('leaderboard-metric')?.addEventListener('change', loadLeaderboard);
document.getElementById('refresh-leaderboard')?.addEventListener('click', loadLeaderboard);

// My Statistics Section
async function loadMyStats() {
    document.getElementById('my-account-id').textContent = `Account: ${currentAccountId}`;
    
    const data = await apiGet(`stats/${currentAccountId}`);
    
    if (data && data.status === 'success') {
        displayMyStats(data.data);
    } else {
        showNotification('Account not found. Loading demo data.', 'warning');
        displayDemoStats();
    }
}

function displayMyStats(stats) {
    const netProfit = (stats.total_profit || 0) + (stats.total_loss || 0);
    const profitChange = stats.initial_balance ? 
        ((stats.current_balance - stats.initial_balance) / stats.initial_balance * 100) : 0;
    
    document.getElementById('my-profit').textContent = formatCurrency(netProfit);
    document.getElementById('my-profit-change').textContent = `${profitChange >= 0 ? '+' : ''}${profitChange.toFixed(2)}%`;
    document.getElementById('my-profit-change').className = `stat-change ${profitChange >= 0 ? 'positive' : 'negative'}`;
    
    document.getElementById('my-win-rate').textContent = formatPercent(stats.win_rate || 0);
    document.getElementById('my-profit-factor').textContent = (stats.profit_factor || 0).toFixed(2);
    document.getElementById('my-total-trades').textContent = stats.total_trades || 0;
    document.getElementById('my-max-drawdown').textContent = formatPercent(stats.max_drawdown || 0);
    document.getElementById('my-win-streak').textContent = `${stats.consecutive_wins || 0} wins`;
    
    // Create charts
    createEquityChart(stats);
    createWinLossChart(stats);
}

function displayDemoStats() {
    // Demo data for testing
    const demoStats = {
        total_profit: 2500,
        total_loss: -800,
        win_rate: 65,
        profit_factor: 2.3,
        total_trades: 150,
        max_drawdown: 8.5,
        consecutive_wins: 7,
        winning_trades: 98,
        losing_trades: 52,
        initial_balance: 10000,
        current_balance: 11700
    };
    
    displayMyStats(demoStats);
}

function createEquityChart(stats) {
    const ctx = document.getElementById('equity-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (charts.equity) {
        charts.equity.destroy();
    }
    
    // Generate sample equity curve
    const days = 30;
    const labels = [];
    const data = [];
    let balance = stats.initial_balance || 10000;
    
    for (let i = 0; i < days; i++) {
        labels.push(`Day ${i + 1}`);
        balance += (Math.random() - 0.4) * 200;
        data.push(balance);
    }
    
    charts.equity = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Equity',
                data: data,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    ticks: {
                        color: '#cbd5e1',
                        callback: function(value) {
                            return '$' + value.toFixed(0);
                        }
                    },
                    grid: {
                        color: '#334155'
                    }
                },
                x: {
                    ticks: {
                        color: '#cbd5e1'
                    },
                    grid: {
                        color: '#334155'
                    }
                }
            }
        }
    });
}

function createWinLossChart(stats) {
    const ctx = document.getElementById('win-loss-chart');
    if (!ctx) return;
    
    if (charts.winLoss) {
        charts.winLoss.destroy();
    }
    
    charts.winLoss = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Wins', 'Losses'],
            datasets: [{
                data: [stats.winning_trades || 0, stats.losing_trades || 0],
                backgroundColor: ['#10b981', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#cbd5e1'
                    }
                }
            }
        }
    });
}

// Backtests Section
async function loadBacktests() {
    const data = await apiGet(`backtests?account_id=${currentAccountId}&limit=20`);
    
    if (data && data.status === 'success') {
        displayBacktests(data.data);
    }
}

function displayBacktests(backtests) {
    const container = document.getElementById('backtests-list');
    
    if (!backtests || backtests.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔬</div><div class="empty-state-text">No backtests yet</div></div>';
        return;
    }
    
    let html = '';
    backtests.forEach(backtest => {
        const roi = ((backtest.final_balance - backtest.initial_balance) / backtest.initial_balance * 100).toFixed(2);
        const profitClass = roi >= 0 ? 'profit-positive' : 'profit-negative';
        
        html += `
            <div class="backtest-card">
                <h3>${backtest.strategy_name}</h3>
                <p style="color: var(--text-secondary);">
                    ${backtest.start_date} to ${backtest.end_date}
                </p>
                <div class="backtest-stats">
                    <div class="backtest-stat">
                        <span class="backtest-stat-label">ROI</span>
                        <span class="backtest-stat-value ${profitClass}">${roi}%</span>
                    </div>
                    <div class="backtest-stat">
                        <span class="backtest-stat-label">Win Rate</span>
                        <span class="backtest-stat-value">${formatPercent(backtest.win_rate)}</span>
                    </div>
                    <div class="backtest-stat">
                        <span class="backtest-stat-label">Profit Factor</span>
                        <span class="backtest-stat-value">${backtest.profit_factor.toFixed(2)}</span>
                    </div>
                    <div class="backtest-stat">
                        <span class="backtest-stat-label">Total Trades</span>
                        <span class="backtest-stat-value">${backtest.total_trades}</span>
                    </div>
                    <div class="backtest-stat">
                        <span class="backtest-stat-label">Max Drawdown</span>
                        <span class="backtest-stat-value">${formatPercent(backtest.max_drawdown)}</span>
                    </div>
                    <div class="backtest-stat">
                        <span class="backtest-stat-label">Sharpe Ratio</span>
                        <span class="backtest-stat-value">${backtest.sharpe_ratio?.toFixed(2) || 'N/A'}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Trade History Section
async function loadTrades() {
    const data = await apiGet(`trades/${currentAccountId}?limit=100`);
    
    if (data && data.status === 'success') {
        displayTrades(data.data);
    }
}

function displayTrades(trades) {
    const tbody = document.getElementById('trades-body');
    
    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state"><p>No trades yet</p></td></tr>';
        return;
    }
    
    let html = '';
    trades.forEach(trade => {
        const profitClass = trade.profit >= 0 ? 'profit-positive' : 'profit-negative';
        const duration = trade.duration_hours ? `${trade.duration_hours.toFixed(1)}h` : 'N/A';
        
        html += `
            <tr>
                <td>#${trade.signal_number || 'N/A'}</td>
                <td><strong>${trade.symbol}</strong></td>
                <td><span class="badge-${trade.action.toLowerCase()}">${trade.action}</span></td>
                <td>${trade.entry_price?.toFixed(5) || 'N/A'}</td>
                <td>${trade.exit_price?.toFixed(5) || 'N/A'}</td>
                <td>${trade.lots?.toFixed(2)}</td>
                <td class="${profitClass}">${formatCurrency(trade.profit)}</td>
                <td class="${profitClass}">${trade.pips ? trade.pips.toFixed(1) : 'N/A'}</td>
                <td>${duration}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

// Utility Functions
function formatCurrency(value) {
    if (value === null || value === undefined) return '$0.00';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

function formatPercent(value) {
    if (value === null || value === undefined) return '0%';
    return `${value.toFixed(1)}%`;
}

function formatNumber(value) {
    if (value === null || value === undefined) return '0';
    return new Intl.NumberFormat('en-US').format(value);
}

function showNotification(message, type = 'info') {
    // Simple notification (can be enhanced with a toast library)
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // You can add a toast notification here
    alert(message);
}

// Backtest Form Functions
function initializeBacktestForm() {
    const runButton = document.getElementById('run-backtest-btn');
    
    if (runButton) {
        runButton.addEventListener('click', runBacktest);
    }
}

async function runBacktest() {
    const startDate = document.getElementById('backtest-start-date').value;
    const endDate = document.getElementById('backtest-end-date').value;
    const balance = parseFloat(document.getElementById('backtest-balance').value);
    const risk = parseFloat(document.getElementById('backtest-risk').value);
    const compound = document.getElementById('backtest-compound').checked;
    const saveResult = document.getElementById('backtest-save').checked;
    
    if (!startDate || !endDate) {
        alert('Please select start and end dates');
        return;
    }
    
    if (balance < 100) {
        alert('Starting balance must be at least $100');
        return;
    }
    
    if (risk < 0.1 || risk > 20) {
        alert('Risk must be between 0.1% and 20%');
        return;
    }
    
    // Show loading
    document.getElementById('backtest-loading').style.display = 'inline-block';
    document.getElementById('run-backtest-btn').disabled = true;
    document.getElementById('backtest-results').style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/api/run-backtest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate,
                initial_balance: balance,
                risk_percent: risk,
                compound: compound,
                save_result: saveResult,
                account_id: currentAccountId
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayBacktestResults(data);
            showNotification(`Backtest complete! ${data.stats.total_trades} trades simulated`, 'success');
        } else {
            showNotification(`Backtest failed: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error('Error running backtest:', error);
        showNotification('Failed to run backtest. Make sure backend is running.', 'error');
    } finally {
        document.getElementById('backtest-loading').style.display = 'none';
        document.getElementById('run-backtest-btn').disabled = false;
    }
}

function displayBacktestResults(data) {
    const stats = data.stats;
    
    // Show results section
    document.getElementById('backtest-results').style.display = 'block';
    
    // Update stats cards
    const roiClass = stats.roi >= 0 ? 'positive' : 'negative';
    document.getElementById('bt-final-balance').textContent = formatCurrency(stats.final_balance);
    document.getElementById('bt-roi').textContent = `${stats.roi >= 0 ? '+' : ''}${stats.roi.toFixed(2)}%`;
    document.getElementById('bt-roi').className = `stat-change ${roiClass}`;
    
    document.getElementById('bt-win-rate').textContent = `${stats.win_rate.toFixed(1)}%`;
    document.getElementById('bt-profit-factor').textContent = stats.profit_factor.toFixed(2);
    document.getElementById('bt-total-trades').textContent = stats.total_trades;
    document.getElementById('bt-max-dd').textContent = `${stats.max_drawdown.toFixed(1)}%`;
    document.getElementById('bt-sharpe').textContent = stats.sharpe_ratio ? stats.sharpe_ratio.toFixed(2) : 'N/A';
    
    // Create equity chart
    createBacktestEquityChart(data.equity_curve);
    
    // Create TP distribution chart
    createTPDistributionChart(stats.tp_distribution);
    
    // Display trade list
    displayBacktestTrades(data.trades);
    
    // Scroll to results
    document.getElementById('backtest-results').scrollIntoView({ behavior: 'smooth' });
}

function createBacktestEquityChart(equityCurve) {
    const ctx = document.getElementById('backtest-equity-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (charts.backtestEquity) {
        charts.backtestEquity.destroy();
    }
    
    const labels = equityCurve.map((point, index) => {
        if (index === 0) return 'Start';
        if (index === equityCurve.length - 1) return 'End';
        return ''; // Hide middle labels for clarity
    });
    
    const data = equityCurve.map(point => point.balance);
    const color = data[data.length - 1] >= data[0] ? '#10b981' : '#ef4444';
    
    charts.backtestEquity = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Balance',
                data: data,
                borderColor: color,
                backgroundColor: color + '20',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Balance: $' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        color: '#cbd5e1',
                        callback: function(value) {
                            return '$' + value.toFixed(0);
                        }
                    },
                    grid: {
                        color: '#334155'
                    }
                },
                x: {
                    ticks: {
                        color: '#cbd5e1'
                    },
                    grid: {
                        color: '#334155'
                    }
                }
            }
        }
    });
}

function createTPDistributionChart(tpDistribution) {
    const ctx = document.getElementById('backtest-tp-chart');
    if (!ctx) return;
    
    if (charts.backtestTP) {
        charts.backtestTP.destroy();
    }
    
    const labels = Object.keys(tpDistribution);
    const data = Object.values(tpDistribution);
    const colors = ['#ef4444', '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899'];
    
    charts.backtestTP = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#cbd5e1'
                    }
                }
            }
        }
    });
}

function displayBacktestTrades(trades) {
    const tbody = document.getElementById('backtest-trades-body');
    
    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state"><p>No trades</p></td></tr>';
        return;
    }
    
    let html = '';
    trades.forEach(trade => {
        const profitClass = trade.profit >= 0 ? 'profit-positive' : 'profit-negative';
        const tpLabel = trade.tp_hit === 0 ? 'SL' : `TP${trade.tp_hit}`;
        
        html += `
            <tr>
                <td>#${trade.signal_number}</td>
                <td><strong>${trade.symbol}</strong></td>
                <td><span class="badge-${trade.action.toLowerCase()}">${trade.action}</span></td>
                <td>${trade.entry_price.toFixed(5)}</td>
                <td>${trade.exit_price.toFixed(5)}</td>
                <td><span class="badge-${trade.tp_hit === 0 ? 'sell' : 'buy'}">${tpLabel}</span></td>
                <td>${trade.lots.toFixed(2)}</td>
                <td class="${profitClass}">${formatCurrency(trade.profit)}</td>
                <td>${formatCurrency(trade.balance_after)}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

// Signal History Management
let currentSignalPage = 1;
const signalsPerPage = 50;
let totalSignalCount = 0;

async function loadSignalHistory(page = 1) {
    try {
        const offset = (page - 1) * signalsPerPage;
        const response = await fetch(`${API_BASE}/api/signal-history?limit=${signalsPerPage}&offset=${offset}`);
        const result = await response.json();
        
        if (result.status === 'success') {
            const data = result.data;
            currentSignalPage = page;
            totalSignalCount = data.total_count;
            
            // Update summary stats
            if (data.summary) {
                document.getElementById('signal-total').textContent = data.summary.total_signals || 0;
                document.getElementById('signal-wins').textContent = data.summary.winning_signals || 0;
                document.getElementById('signal-losses').textContent = data.summary.losing_signals || 0;
                document.getElementById('signal-win-rate').textContent = 
                    (data.summary.win_rate || 0).toFixed(1) + '%';
                
                // Update Total P/L %
                const totalPL = data.summary.total_pl_percent || 0;
                const totalPLElement = document.getElementById('signal-total-pl');
                totalPLElement.textContent = (totalPL >= 0 ? '+' : '') + totalPL.toFixed(2) + '%';
                totalPLElement.style.color = totalPL >= 0 ? '#10b981' : '#ef4444';
            }
            
            // Display signals
            displaySignals(data.signals);
            
            // Update pagination
            updateSignalPagination();
        } else {
            showError('Failed to load signal history');
        }
    } catch (error) {
        console.error('Error loading signal history:', error);
        showError('Error loading signal history');
    }
}

function displaySignals(signals) {
    const tbody = document.getElementById('signal-history-body');
    
    if (!signals || signals.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state"><p>No signals found</p></td></tr>';
        return;
    }
    
    let html = '';
    signals.forEach((signal, index) => {
        const signalNum = totalSignalCount - ((currentSignalPage - 1) * signalsPerPage) - index;
        const actionBadge = signal.action === 'BUY' ? 'badge-buy' : 'badge-sell';
        
        // Determine outcome badge style
        let outcomeBadge = 'badge-sell'; // Default for SL
        if (signal.outcome && signal.outcome.includes('TP')) {
            outcomeBadge = 'badge-buy'; // Green for TP hits
        }
        
        // Format entry and exit prices
        const entry = parseFloat(signal.entry_price).toFixed(5);
        let exit = 'N/A';
        
        if (signal.exit_price) {
            exit = parseFloat(signal.exit_price).toFixed(5);
        }
        
        // Format pips
        const pipsClass = signal.pips >= 0 ? 'profit-positive' : 'profit-negative';
        const pipsDisplay = signal.pips ? `${signal.pips > 0 ? '+' : ''}${signal.pips.toFixed(1)}` : '0.0';
        
        // Format profit %
        const profitClass = signal.profit_percent >= 0 ? 'profit-positive' : 'profit-negative';
        const profitDisplay = signal.profit_percent ? `${signal.profit_percent > 0 ? '+' : ''}${signal.profit_percent.toFixed(2)}%` : '0.00%';
        
        // Format dates
        const entryDate = signal.created_at ? new Date(signal.created_at).toLocaleDateString() : 'N/A';
        const exitDate = signal.exit_date ? new Date(signal.exit_date).toLocaleDateString() : (signal.outcome === 'SL Hit' ? 'SL' : 'N/A');
        
        html += `
            <tr>
                <td>${signalNum}</td>
                <td><strong>${signal.symbol || 'N/A'}</strong></td>
                <td><span class="${actionBadge}">${signal.action || 'N/A'}</span></td>
                <td>${entry}</td>
                <td>${exit}</td>
                <td class="${pipsClass}">${pipsDisplay}</td>
                <td class="${profitClass}"><strong>${profitDisplay}</strong></td>
                <td><span class="${outcomeBadge}">${signal.outcome || 'Pending'}</span></td>
                <td>${entryDate}</td>
                <td>${exitDate}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

function updateSignalPagination() {
    const totalPages = Math.ceil(totalSignalCount / signalsPerPage);
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageInfo = document.getElementById('page-info');
    
    // Update page info
    pageInfo.textContent = `Page ${currentSignalPage} of ${totalPages}`;
    
    // Update button states
    prevBtn.disabled = currentSignalPage <= 1;
    nextBtn.disabled = currentSignalPage >= totalPages;
}

// Initialize signal history event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Load signal history when page loads
    loadSignalHistory(1);
    
    // Refresh button
    const refreshBtn = document.getElementById('refresh-signals-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadSignalHistory(currentSignalPage));
    }
    
    // Pagination buttons
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentSignalPage > 1) {
                loadSignalHistory(currentSignalPage - 1);
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const totalPages = Math.ceil(totalSignalCount / signalsPerPage);
            if (currentSignalPage < totalPages) {
                loadSignalHistory(currentSignalPage + 1);
            }
        });
    }
});

// Auto-refresh data every 30 seconds
setInterval(() => {
    const activeSection = document.querySelector('.content-section.active');
    if (activeSection) {
        const sectionId = activeSection.id.replace('-section', '');
        
        // Only refresh if not on trades or backtests (they don't change often)
        if (['overview', 'leaderboard', 'my-stats'].includes(sectionId)) {
            showSection(sectionId);
        }
    }
}, 30000);

// ==================== STRATEGY CUSTOMIZATION ====================

// Store original signal data for recalculation
let originalSignalData = null;
let plChart = null;

// Default strategy percentages (TP1-TP6)
const DEFAULT_STRATEGY = [50, 20, 10, 10, 10, 0];

// Initialize strategy controls
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners to strategy inputs
    const inputs = ['tp1', 'tp2', 'tp3', 'tp4', 'tp5', 'tp6'];
    inputs.forEach(tp => {
        const input = document.getElementById(`${tp}-percent`);
        if (input) {
            input.addEventListener('input', updateStrategyTotal);
            // Only apply strategy on blur or when user explicitly changes it, not on every keystroke
            input.addEventListener('blur', function() {
                const total = parseFloat(document.getElementById('tp1-percent').value || 0) +
                             parseFloat(document.getElementById('tp2-percent').value || 0) +
                             parseFloat(document.getElementById('tp3-percent').value || 0) +
                             parseFloat(document.getElementById('tp4-percent').value || 0) +
                             parseFloat(document.getElementById('tp5-percent').value || 0) +
                             parseFloat(document.getElementById('tp6-percent').value || 0);
                if (total === 100) {
                    applyCustomStrategy();
                }
            });
        }
    });
    
    // Reset button
    const resetBtn = document.getElementById('reset-strategy-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetStrategy);
    }
    
    // Initialize chart
    initializePLChart();
    
    // Initialize strategy total display
    updateStrategyTotal();
});

// Update total percentage display
function updateStrategyTotal() {
    const tp1 = parseFloat(document.getElementById('tp1-percent').value) || 0;
    const tp2 = parseFloat(document.getElementById('tp2-percent').value) || 0;
    const tp3 = parseFloat(document.getElementById('tp3-percent').value) || 0;
    const tp4 = parseFloat(document.getElementById('tp4-percent').value) || 0;
    const tp5 = parseFloat(document.getElementById('tp5-percent').value) || 0;
    const tp6 = parseFloat(document.getElementById('tp6-percent').value) || 0;
    
    const total = tp1 + tp2 + tp3 + tp4 + tp5 + tp6;
    const totalElement = document.getElementById('strategy-total');
    
    if (totalElement) {
        totalElement.textContent = `Total: ${total.toFixed(0)}%`;
        
        // Color code based on validity
        if (total === 100) {
            totalElement.style.color = '#10b981'; // Green
        } else if (total > 100) {
            totalElement.style.color = '#ef4444'; // Red
        } else {
            totalElement.style.color = '#f59e0b'; // Orange
        }
    }
}

// Reset strategy to defaults
function resetStrategy() {
    document.getElementById('tp1-percent').value = DEFAULT_STRATEGY[0];
    document.getElementById('tp2-percent').value = DEFAULT_STRATEGY[1];
    document.getElementById('tp3-percent').value = DEFAULT_STRATEGY[2];
    document.getElementById('tp4-percent').value = DEFAULT_STRATEGY[3];
    document.getElementById('tp5-percent').value = DEFAULT_STRATEGY[4];
    document.getElementById('tp6-percent').value = DEFAULT_STRATEGY[5];
    
    updateStrategyTotal();
    applyCustomStrategy();
}

// Apply custom strategy and recalculate
function applyCustomStrategy() {
    // Get current percentages
    const tp1 = parseFloat(document.getElementById('tp1-percent').value) || 0;
    const tp2 = parseFloat(document.getElementById('tp2-percent').value) || 0;
    const tp3 = parseFloat(document.getElementById('tp3-percent').value) || 0;
    const tp4 = parseFloat(document.getElementById('tp4-percent').value) || 0;
    const tp5 = parseFloat(document.getElementById('tp5-percent').value) || 0;
    const tp6 = parseFloat(document.getElementById('tp6-percent').value) || 0;
    
    const total = tp1 + tp2 + tp3 + tp4 + tp5 + tp6;
    
    // Validate total
    if (total !== 100) {
        console.warn(`Strategy total is ${total}%, not 100%`);
        return;
    }
    
    // Get strategy array
    const strategy = [tp1/100, tp2/100, tp3/100, tp4/100, tp5/100, tp6/100];
    
    // Recalculate signals with new strategy
    if (originalSignalData && originalSignalData.signals) {
        const recalculatedSignals = recalculateSignals(originalSignalData.signals, strategy);
        const summary = calculateSummary(recalculatedSignals);
        
        // Update display
        updateSignalDisplay(recalculatedSignals, summary);
        updatePLChart(recalculatedSignals);
    }
}

// Recalculate signal profits with custom strategy
function recalculateSignals(signals, strategy) {
    return signals.map(signal => {
        // Copy signal deeply
        const newSignal = JSON.parse(JSON.stringify(signal));
        
        // For SL hits, keep original
        if (newSignal.outcome === 'SL Hit') {
            return newSignal;
        }
        
        // Extract TP number from outcome (e.g., "TP3 Hit" -> 3)
        const tpMatch = newSignal.outcome.match(/TP(\d)/);
        if (!tpMatch) {
            return newSignal;
        }
        
        const tpHit = parseInt(tpMatch[1]);
        
        // Get risk percentage (default to 2% MEDIUM if not specified)
        const riskPercent = signal.risk_level === 'LOW' ? 1 : 
                           signal.risk_level === 'HIGH' ? 3 : 2;
        
        // Recalculate profit based on ACTUAL TP PRICES and new strategy
        let totalProfit = 0;
        const entryPrice = parseFloat(signal.entry_price) || 0;
        
        if (!entryPrice) {
            return newSignal;
        }
        
        // Calculate profit for each TP that was hit using the ACTUAL TP PRICE
        for (let i = 0; i < tpHit; i++) {
            const tpNum = i + 1;
            const tpPrice = parseFloat(signal[`tp${tpNum}`]) || 0;
            
            if (!tpPrice) {
                continue;
            }
            
            // Calculate price movement FROM ENTRY TO THIS TP
            const priceMove = Math.abs(tpPrice - entryPrice);
            const priceMovePercent = (priceMove / entryPrice) * 100;
            const leveragedMove = priceMovePercent * 500; // 500:1 leverage
            
            // Apply NEW strategy percentage for this TP level
            const newPercentage = strategy[i];
            const tpProfit = (leveragedMove * newPercentage) * (riskPercent / 100);
            
            totalProfit += tpProfit;
            
            // Update breakdown if it exists
            if (newSignal.tp_breakdown && newSignal.tp_breakdown[i]) {
                newSignal.tp_breakdown[i].profit_percent = tpProfit;
                newSignal.tp_breakdown[i].partial_exit_percent = Math.round(newPercentage * 100);
            }
        }
        
        newSignal.profit_percent = totalProfit;
        
        return newSignal;
    });
}

// Get original TP percentage from backend logic
function getOriginalTPPercentage(tpNum, hasTP6) {
    const originalStrategy = [0.5, 0.2, 0.1, 0.1, hasTP6 ? 0.05 : 0.1, hasTP6 ? 0.05 : 0];
    return originalStrategy[tpNum - 1] || 0;
}

// Calculate pip value based on symbol
function calculatePipValue(symbol) {
    if (symbol.includes('XAU')) return 1.0;
    if (symbol.includes('BTC')) return 0.1;
    if (symbol.includes('NAS100')) return 0.2;
    return 10.0; // Forex pairs
}

// Calculate summary stats
function calculateSummary(signals) {
    const total = signals.length;
    const wins = signals.filter(s => s.outcome !== 'SL Hit').length;
    const losses = signals.filter(s => s.outcome === 'SL Hit').length;
    const winRate = total > 0 ? (wins / total) * 100 : 0;
    
    const totalPL = signals.reduce((sum, s) => sum + (s.profit_percent || 0), 0);
    
    // Calculate TP distribution
    const tpDist = {
        tp1: 0, tp2: 0, tp3: 0, tp4: 0, tp5: 0, tp6: 0, sl: 0
    };
    
    signals.forEach(s => {
        if (s.outcome === 'SL Hit') {
            tpDist.sl++;
        } else {
            const match = s.outcome.match(/TP(\d)/);
            if (match) {
                const tpNum = parseInt(match[1]);
                tpDist[`tp${tpNum}`]++;
            }
        }
    });
    
    return {
        total_signals: total,
        winning_signals: wins,
        losing_signals: losses,
        win_rate: winRate,
        total_pl_percent: totalPL,
        tp_distribution: tpDist
    };
}

// Update signal display with recalculated data
function updateSignalDisplay(signals, summary) {
    // Update summary stats
    if (summary) {
        document.getElementById('signal-total').textContent = summary.total_signals || 0;
        document.getElementById('signal-wins').textContent = summary.winning_signals || 0;
        document.getElementById('signal-losses').textContent = summary.losing_signals || 0;
        document.getElementById('signal-win-rate').textContent = 
            (summary.win_rate || 0).toFixed(1) + '%';
        
        // Update Total P/L %
        const totalPL = summary.total_pl_percent || 0;
        const totalPLElement = document.getElementById('signal-total-pl');
        if (totalPLElement) {
            totalPLElement.textContent = (totalPL >= 0 ? '+' : '') + totalPL.toFixed(2) + '%';
            totalPLElement.style.color = totalPL >= 0 ? '#10b981' : '#ef4444';
        }
    }
    
    // Update signal table
    displaySignals(signals);
}

// Initialize P/L Chart
function initializePLChart() {
    const ctx = document.getElementById('pl-chart');
    if (!ctx) return;
    
    plChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Cumulative P/L %',
                data: [],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.y;
                            return `P/L: ${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) {
                            return (value >= 0 ? '+' : '') + value.toFixed(0) + '%';
                        }
                    }
                }
            }
        }
    });
}

// Update P/L Chart with signal data
function updatePLChart(signals) {
    if (!plChart) return;
    
    // Sort signals by entry date
    const sortedSignals = [...signals].sort((a, b) => {
        const dateA = new Date(a.entry_date || 0);
        const dateB = new Date(b.entry_date || 0);
        return dateA - dateB;
    });
    
    // Calculate cumulative P/L
    const labels = [];
    const data = [];
    let cumulativePL = 0;
    
    sortedSignals.forEach((signal, index) => {
        cumulativePL += signal.profit_percent || 0;
        
        // Format date
        const date = signal.entry_date ? new Date(signal.entry_date) : null;
        const label = date ? `${date.getMonth() + 1}/${date.getDate()}` : `#${index + 1}`;
        
        labels.push(label);
        data.push(cumulativePL);
    });
    
    // Update chart data
    plChart.data.labels = labels;
    plChart.data.datasets[0].data = data;
    
    // Update line color based on final P/L
    const finalPL = data[data.length - 1] || 0;
    plChart.data.datasets[0].borderColor = finalPL >= 0 ? '#10b981' : '#ef4444';
    plChart.data.datasets[0].backgroundColor = finalPL >= 0 ? 
        'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';
    
    plChart.update();
}

// Override loadSignalHistory to store original data
const originalLoadSignalHistory = loadSignalHistory;
loadSignalHistory = async function(page = 1) {
    await originalLoadSignalHistory(page);
    
    // Fetch full data to store for recalculation
    try {
        const response = await fetch(`${API_BASE}/api/signal-history?limit=1000`);
        const result = await response.json();
        
        if (result.status === 'success') {
            originalSignalData = result.data;
            
            // Initialize chart with original data
            if (originalSignalData.signals) {
                updatePLChart(originalSignalData.signals);
            }
        }
    } catch (error) {
        console.error('Error fetching full signal data:', error);
    }
};

