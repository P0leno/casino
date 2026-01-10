import React, { useState } from 'react';
import './PaymentModal.css';
import LottieAnimation from './LottieAnimation';

function PaymentModal({ isOpen, onClose, invoiceUrl, amount, giftTitle, giftSlug, onCheckPayment }) {
    if (!isOpen) return null;

    const [checking, setChecking] = useState(false);

    // Lottie URL for NFT
    const getLottieUrl = () => {
        return `https://nft.fragment.com/gift/${giftSlug}.lottie.json`;
    };

    const handlePay = () => {
        if (invoiceUrl) {
            window.Telegram.WebApp.openInvoice(invoiceUrl, (status) => {
                if (status === 'paid') {
                    // Auto-check on successful callback (though sometimes it's async)
                    handleCheck();
                }
            });
        }
    };

    const handleCheck = async () => {
        if (checking) return;
        setChecking(true);
        await onCheckPayment();
        setChecking(false);
    };

    return (
        <div className="payment-modal-overlay" onClick={onClose}>
            <div className="payment-modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="payment-modal-spotlight" />
                <button className="payment-modal-close" onClick={onClose}>✕</button>

                <div className="payment-modal-scroll-content">
                    <div className="payment-modal-image-container">
                        <LottieAnimation
                            animationData={getLottieUrl()}
                            width={240}
                            height={240}
                            loop={true}
                            autoplay={true}
                        />
                    </div>

                    <h2 className="payment-modal-title">Требуется комиссия</h2>

                    <p className="payment-modal-description">
                        Для передачи этого NFT (<b>{giftTitle}</b>) требуется оплатить комиссию сети.
                    </p>
                </div>

                <div className="payment-modal-actions">
                    <button className="payment-modal-pay-btn" onClick={handlePay}>
                        Оплатить
                    </button>
                    <button className="payment-modal-check-btn" onClick={handleCheck} disabled={checking}>
                        {checking ? 'Проверка...' : 'Проверить оплату'}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default PaymentModal;
