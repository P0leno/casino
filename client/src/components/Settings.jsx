import { useState, useEffect } from 'react';
import './Settings.css';

const Settings = () => {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [restarting, setRestarting] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const [isAutoWithdrawExpanded, setIsAutoWithdrawExpanded] = useState(false);

  // Helper for mixed boolean types (1/0 vs true/false)
  const isTrue = (val) => val === '1' || val === 'true';

  const loadSettings = async () => {
    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 сек таймаут

      const response = await fetch('/api/get-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const text = await response.text();
        console.error('Response not OK:', response.status, text);
        throw new Error(`HTTP ${response.status}: ${text.substring(0, 100)}`);
      }

      const text = await response.text();
      console.log('Response text:', text);

      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        console.error('JSON parse error:', e, 'Text:', text);
        throw new Error('Сервер вернул некорректный ответ');
      }

      if (data.valid && data.settings) {
        setSettings(data.settings);
        // Получаем статус тех работ из настроек
        setMaintenanceMode(data.maintenanceMode || false);
      } else {
        tg.showAlert(data.error || 'Ошибка загрузки настроек');
      }
    } catch (error) {
      console.error('Error loading settings:', error);
      const tg = window.Telegram.WebApp;
      if (error.name === 'AbortError') {
        tg.showAlert('Превышено время ожидания. Попробуйте позже.');
      } else {
        tg.showAlert('Ошибка загрузки настроек: ' + error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleMaintenance = async () => {
    if (saving) return;

    setSaving(true);

    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;

      // Используем update-setting вместо toggle-maintenance
      const newValue = maintenanceMode ? '0' : '1';

      const response = await fetch('/api/update-setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          key: 'maintenance_mode',
          value: newValue
        })
      });

      const data = await response.json();

      if (data.success) {
        const newMode = newValue === '1';
        setMaintenanceMode(newMode);

        // Обновляем локальное состояние settings
        setSettings(prev => ({
          ...prev,
          maintenance_mode: {
            ...prev.maintenance_mode,
            value: newValue
          }
        }));

        tg.HapticFeedback.notificationOccurred('success');

        const status = newMode ? 'включен' : 'выключен';
        tg.showAlert?.(`Режим технических работ ${status}`);
      } else {
        tg.showAlert?.(data.message || 'Ошибка переключения режима');
        tg.HapticFeedback.notificationOccurred('error');
      }
    } catch (error) {
      console.error('Error toggling maintenance:', error);
      window.Telegram.WebApp.showAlert?.('Ошибка переключения режима');
      window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
    } finally {
      setSaving(false);
    }
  };

  const updateCommission = async (newValue) => {
    if (saving) return;

    // Валидация
    const numValue = parseFloat(newValue);
    if (isNaN(numValue) || numValue < 0 || numValue > 100) return;

    setSaving(true);

    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;

      const response = await fetch('/api/update-setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          key: 'shop_commission',
          value: String(numValue)
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Обновляем локальное состояние
        setSettings(prev => ({
          ...prev,
          shop_commission: {
            ...prev.shop_commission,
            value: String(numValue)
          }
        }));

        // Уведомление об успешном пересчете
        tg.showAlert?.(`Наценка изменена на ${numValue}%. Цены пересчитываются...`);
      } else {
        tg.showAlert?.(data.error || 'Ошибка сохранения');
      }
    } catch (error) {
      console.error('Error updating commission:', error);
      window.Telegram.WebApp.showAlert?.('Ошибка соединения');
    } finally {
      setSaving(false);
    }
  };

  const updateSellCommission = async (newValue) => {
    if (saving) return;

    // Валидация
    const numValue = parseFloat(newValue);
    if (isNaN(numValue) || numValue < 0 || numValue > 100) return;

    setSaving(true);

    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;

      const response = await fetch('/api/update-setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          key: 'sell_commission',
          value: String(numValue)
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Обновляем локальное состояние
        setSettings(prev => ({
          ...prev,
          sell_commission: {
            ...prev.sell_commission,
            value: String(numValue)
          }
        }));

        tg.showAlert?.(`Комиссия на продажу изменена на ${numValue}%`);
      } else {
        tg.showAlert?.(data.error || 'Ошибка сохранения');
      }
    } catch (error) {
      console.error('Error updating sell commission:', error);
      window.Telegram.WebApp.showAlert?.('Ошибка соединения');
    } finally {
      setSaving(false);
    }
  };

  const updateCustomPromoRefs = async (newValue) => {
    if (saving) return;

    // Валидация - только целые числа
    const numValue = parseInt(newValue);
    if (isNaN(numValue) || numValue < 1 || numValue > 1000) return;

    setSaving(true);

    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;

      const response = await fetch('/api/update-setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          key: 'custom_promo_refs_required',
          value: String(numValue)
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Обновляем локальное состояние
        setSettings(prev => ({
          ...prev,
          custom_promo_refs_required: {
            ...prev.custom_promo_refs_required,
            value: String(numValue)
          }
        }));

        tg.showAlert?.(`Требование изменено на ${numValue} рефералов`);
      } else {
        tg.showAlert?.(data.error || 'Ошибка сохранения');
      }
    } catch (error) {
      console.error('Error updating custom promo refs:', error);
      window.Telegram.WebApp.showAlert?.('Ошибка соединения');
    } finally {
      setSaving(false);
    }
  };

  const toggleSetting = async (key, currentValue) => {
    setSaving(true);

    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;

      // Переключаем значение
      const newValue = currentValue === 'true' ? 'false' : 'true';

      const response = await fetch('/api/update-setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData,
          key,
          value: newValue
        })
      });

      const data = await response.json();

      if (data.success) {
        // Обновляем локальное состояние
        setSettings(prev => ({
          ...prev,
          [key]: {
            ...prev[key],
            value: newValue
          }
        }));

        tg.HapticFeedback.notificationOccurred('success');
      } else {
        tg.showAlert(data.message || 'Ошибка обновления настройки');
        tg.HapticFeedback.notificationOccurred('error');
      }
    } catch (error) {
      console.error('Error updating setting:', error);
      window.Telegram.WebApp.showAlert('Ошибка обновления настройки');
      window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
    } finally {
      setSaving(false);
    }
  };

  const handleRestart = async () => {
    const tg = window.Telegram.WebApp;

    // Подтверждение
    const confirmed = await new Promise(resolve =>
      tg.showConfirm('Перезапустить сервер? Текущий раунд краша завершится, затем сервер перезагрузится с новым кодом.', resolve)
    );

    if (!confirmed) return;

    setRestarting(true);

    try {
      const initData = tg.initData;

      const response = await fetch('/api/restart-server', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      });

      const data = await response.json();

      if (data.success) {
        tg.showAlert('Рестарт запущен! Сервер перезагрузится через ~30-60 сек');
        tg.HapticFeedback.notificationOccurred('success');
      } else {
        tg.showAlert(data.message || 'Ошибка запуска рестарта');
        tg.HapticFeedback.notificationOccurred('error');
        setRestarting(false);
      }
    } catch (error) {
      console.error('Error restarting server:', error);
      tg.showAlert('Ошибка соединения');
      tg.HapticFeedback.notificationOccurred('error');
      setRestarting(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-container">
        <div className="settings-loading">
          <div className="spinner"></div>
          <p>Загрузка настроек...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h2>⚙️ Настройки</h2>
        <p className="settings-subtitle">Управление системными параметрами</p>

        {/* Кнопка рестарта */}
        <button
          className="restart-server-button"
          onClick={handleRestart}
          disabled={restarting || saving}
        >
          <span className="restart-icon">🔄</span>
          <span className="restart-text">{restarting ? 'Перезапуск...' : 'Рестарт сервера'}</span>
        </button>
      </div>

      <div className="settings-list">
        {/* Режим технических работ */}
        <div className="setting-item">
          <div className="setting-info">
            <div className="setting-icon">🔧</div>
            <div className="setting-details">
              <div className="setting-name">Технические работы</div>
              <div className="setting-status">
                {maintenanceMode ?
                  <span className="status-enabled">✓ Включен</span> :
                  <span className="status-disabled">✗ Выключен</span>
                }
              </div>
            </div>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={maintenanceMode}
              onChange={toggleMaintenance}
              disabled={saving}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        {/* Авто-выдача (Auto-Withdraw) */}
        <div className={`setting-item auto-withdraw-card ${isAutoWithdrawExpanded ? 'expanded' : ''}`}>
          <div
            className="setting-header-click-area"
            onClick={(e) => {
              // Prevent collapse when clicking the switch
              if (e.target.closest('.toggle-switch')) return;
              setIsAutoWithdrawExpanded(!isAutoWithdrawExpanded);
            }}
          >
            <div className="setting-info">
              <div className="setting-icon">💸</div>
              <div className="setting-details">
                <div className="setting-name">Авто-выдача</div>
                <div className="setting-status">
                  {(isTrue(settings.withdraw_regular_enabled?.value) && isTrue(settings.withdraw_nft_enabled?.value)) ?
                    <span className="status-enabled">✓ Включена</span> :
                    <span className="status-disabled">✗ Выключена</span>
                  }
                </div>
              </div>
            </div>

            <div className="setting-controls-right">
              {/* Global Switch */}
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={isTrue(settings.withdraw_regular_enabled?.value) && isTrue(settings.withdraw_nft_enabled?.value)}
                  onChange={() => {
                    const isEnabled = isTrue(settings.withdraw_regular_enabled?.value) && isTrue(settings.withdraw_nft_enabled?.value);
                    const newValue = isEnabled ? '0' : '1';

                    // Manually call API for both
                    const tg = window.Telegram.WebApp;
                    const initData = tg.initData;

                    // Helper to update
                    const update = async (key, val) => {
                      await fetch('/api/update-setting', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ initData, key, value: val })
                      });
                      setSettings(prev => ({
                        ...prev,
                        [key]: { ...prev[key], value: val }
                      }));
                    };

                    update('withdraw_regular_enabled', newValue);
                    update('withdraw_nft_enabled', newValue);
                  }}
                  disabled={saving}
                />
                <span className="toggle-slider"></span>
              </label>

              {/* Chevron */}
              <div className={`setting-chevron ${isAutoWithdrawExpanded ? 'rotated' : ''}`}>
                ▼
              </div>
            </div>
          </div>

          {/* Expanded Content */}
          {isAutoWithdrawExpanded && (
            <div className="setting-sub-items">
              {/* Regular */}
              <div className="setting-sub-item">
                <span>Обычные подарки</span>
                <label className="toggle-switch small">
                  <input
                    type="checkbox"
                    checked={isTrue(settings.withdraw_regular_enabled?.value)}
                    onChange={() => toggleSetting('withdraw_regular_enabled', isTrue(settings.withdraw_regular_enabled?.value) ? 'true' : 'false')}
                    disabled={saving}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>

              {/* NFT */}
              <div className="setting-sub-item">
                <span>NFT Подарки</span>
                <label className="toggle-switch small">
                  <input
                    type="checkbox"
                    checked={isTrue(settings.withdraw_nft_enabled?.value)}
                    onChange={() => toggleSetting('withdraw_nft_enabled', isTrue(settings.withdraw_nft_enabled?.value) ? 'true' : 'false')}
                    disabled={saving}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
            </div>
          )}
        </div>

        {settings.stars_topup_enabled && (
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-icon">⭐</div>
              <div className="setting-details">
                <div className="setting-name">{settings.stars_topup_enabled.description}</div>
                <div className="setting-status">
                  {settings.stars_topup_enabled.value === 'true' ?
                    <span className="status-enabled">✓ Включено</span> :
                    <span className="status-disabled">✗ Выключено</span>
                  }
                </div>
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.stars_topup_enabled.value === 'true'}
                onChange={() => toggleSetting('stars_topup_enabled', settings.stars_topup_enabled.value)}
                disabled={saving}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        )}

        {/* Наценка на подарки */}
        {settings.shop_commission && (
          <div className="setting-item-value">
            <div className="setting-info">
              <div className="setting-icon">💰</div>
              <div className="setting-details">
                <div className="setting-name">{settings.shop_commission.description}</div>
                <div className="setting-value-display">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    value={settings.shop_commission.value}
                    onChange={(e) => updateCommission(e.target.value)}
                    disabled={saving}
                    className="commission-input"
                  />
                  <span className="percent-sign">%</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Комиссия на продажу */}
        {settings.sell_commission && (
          <div className="setting-item-value">
            <div className="setting-info">
              <div className="setting-icon">💸</div>
              <div className="setting-details">
                <div className="setting-name">{settings.sell_commission.description}</div>
                <div className="setting-value-display">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    value={settings.sell_commission.value}
                    onChange={(e) => updateSellCommission(e.target.value)}
                    disabled={saving}
                    className="commission-input"
                  />
                  <span className="percent-sign">%</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Рефералов для именного промокода */}
        {settings.custom_promo_refs_required && (
          <div className="setting-item-value">
            <div className="setting-info">
              <div className="setting-icon">👥</div>
              <div className="setting-details">
                <div className="setting-name">{settings.custom_promo_refs_required.description}</div>
                <div className="setting-value-display">
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    step="1"
                    value={settings.custom_promo_refs_required.value}
                    onChange={(e) => updateCustomPromoRefs(e.target.value)}
                    disabled={saving}
                    className="commission-input"
                  />
                  <span className="percent-sign">шт</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {saving && (
        <div className="saving-overlay">
          <div className="spinner"></div>
          <p>Сохранение...</p>
        </div>
      )}
    </div>
  );
};

export default Settings;
