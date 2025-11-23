import { useState, useEffect } from 'react';
import './Settings.css';

const Settings = () => {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [maintenanceMode, setMaintenanceMode] = useState(false);

  useEffect(() => {
    loadSettings();
    loadMaintenanceStatus();
  }, []);

  const loadSettings = async () => {
    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 сек таймаут

      const response = await fetch('https://api.shelloch.xyz/api/get-settings', {
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

  const loadMaintenanceStatus = async () => {
    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;

      const response = await fetch('https://api.shelloch.xyz/api/get-maintenance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      });

      const data = await response.json();
      
      if (data.success) {
        setMaintenanceMode(data.maintenance_mode);
      }
    } catch (error) {
      console.error('Error loading maintenance status:', error);
    }
  };

  const toggleMaintenance = async () => {
    if (saving) return;
    
    setSaving(true);
    
    try {
      const tg = window.Telegram.WebApp;
      const initData = tg.initData;
      
      const response = await fetch('https://api.shelloch.xyz/api/toggle-maintenance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      });

      const data = await response.json();
      
      if (data.success) {
        setMaintenanceMode(data.maintenance_mode);
        tg.HapticFeedback.notificationOccurred('success');
        
        const status = data.maintenance_mode ? 'включен' : 'выключен';
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
      
      const response = await fetch('https://api.shelloch.xyz/api/update-setting', {
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
      
      const response = await fetch('https://api.shelloch.xyz/api/update-setting', {
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
      
      const response = await fetch('https://api.shelloch.xyz/api/update-setting', {
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
      
      const response = await fetch('https://api.shelloch.xyz/api/update-setting', {
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

        {/* Пополнение звездами */}
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
