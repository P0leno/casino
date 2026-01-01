import React, { useState, useEffect } from 'react'
import './ActionStatusModal.css'

function ActionStatusModal({
    isOpen,
    onClose,
    title,
    message,
    actionButtonText,
    onAction,
    secondaryButtonText,
    onSecondaryAction,
    helpText,
    helpLink,
    isError = false,
    icon = '⚠️'
}) {
    const [isClosing, setIsClosing] = useState(false)
    const [render, setRender] = useState(isOpen)

    useEffect(() => {
        if (isOpen) {
            setRender(true)
            setIsClosing(false)
        } else if (render) {
            handleClose()
        }
    }, [isOpen])

    const handleClose = () => {
        setIsClosing(true)
        setTimeout(() => {
            setRender(false)
            onClose()
        }, 300)
    }

    const handleAction = () => {
        if (onAction) onAction()
    }

    if (!render) return null

    return (
        <div
            className={`action-status-overlay ${isClosing ? 'action-status-overlay-closing' : ''}`}
            onClick={handleClose}
        >
            <div
                className={`action-status-content ${isClosing ? 'action-status-content-closing' : ''}`}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Spotlight Effect */}
                <div className="action-status-spotlight" />

                <button className="action-status-close" onClick={handleClose}>
                    ✕
                </button>

                <div className="action-status-body">
                    <div className="action-status-icon">{icon}</div>
                    <h2 className="action-status-title">{title}</h2>
                    <p className="action-status-message">{message}</p>

                    {/* Buttons Container */}
                    <div className="action-status-buttons">
                        {actionButtonText && (
                            <button
                                className="action-status-btn primary"
                                onClick={handleAction}
                            >
                                {actionButtonText}
                            </button>
                        )}

                        {secondaryButtonText && (
                            <button
                                className="action-status-btn secondary"
                                onClick={() => {
                                    if (onSecondaryAction) onSecondaryAction()
                                }}
                            >
                                {secondaryButtonText}
                            </button>
                        )}
                    </div>

                    {/* Help Link */}
                    {helpText && helpLink && (
                        <div className="action-status-help">
                            <a href={helpLink} target="_blank" rel="noopener noreferrer">
                                {helpText}
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default ActionStatusModal
