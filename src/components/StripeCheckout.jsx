import React, { useState, useEffect } from 'react'
import { createCheckoutSession, getPackages } from '../lib/api'
import { CreditCard, Loader2, X, Check, Star, Zap, Infinity } from 'lucide-react'
import BoltIcon from './BoltIcon'

export default function StripeCheckout({ userId, email, onClose, onSuccess }) {
  const [packages, setPackages] = useState(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(null)
  const [error, setError] = useState('')
  const [showSubscriptions, setShowSubscriptions] = useState(false)

  useEffect(() => {
    loadPackages()
  }, [])

  const loadPackages = async () => {
    try {
      const data = await getPackages()
      setPackages(data)
    } catch (err) {
      setError('Failed to load pricing')
    } finally {
      setLoading(false)
    }
  }

  const handlePurchase = async (packageId) => {
    setProcessing(packageId)
    setError('')
    try {
      const result = await createCheckoutSession(packageId, userId, email)
      if (!result?.url) {
        setError('Failed to initialize checkout. Please try again.')
        setProcessing(null)
        return
      }
      window.location.href = result.url
    } catch (err) {
      setError(err.message || 'Failed to start checkout')
      setProcessing(null)
    }
  }

  const creditPackages = [
    {
      id: 'starter',
      name: 'Starter',
      price: '$9.99',
      credits: 5,
      description: 'Perfect for trying out',
      popular: false,
    },
    {
      id: 'popular',
      name: 'Popular',
      price: '$24.99',
      credits: 20,
      description: 'Best value per scan',
      popular: true,
    },
    {
      id: 'value',
      name: 'Value',
      price: '$39.99',
      credits: 50,
      description: 'Great for creators',
      popular: false,
    },
    {
      id: 'pro',
      name: 'Pro',
      price: '$59.99',
      credits: 100,
      description: 'For power users',
      popular: false,
    },
  ]

  const subscriptionPlans = [
    {
      id: 'hobby_monthly',
      name: 'Hobby',
      price: '$9.99/mo',
      scans: 50,
      description: '50 scans per month',
      isUnlimited: false,
      popular: false,
    },
    {
      id: 'pro_monthly',
      name: 'Pro',
      price: '$24.99/mo',
      scans: 200,
      description: '200 scans per month',
      isUnlimited: false,
      popular: true,
    },
    {
      id: 'enterprise_monthly',
      name: 'Enterprise',
      price: '$49.99/mo',
      scans: 'Unlimited',
      description: 'Unlimited scans per month',
      isUnlimited: true,
      popular: false,
    },
  ]

  return (
    <div className="stripe-modal-overlay" onClick={onClose}>
      <div className="stripe-modal" onClick={(e) => e.stopPropagation()}>
        <div className="stripe-modal-header">
          <div className="stripe-modal-title">
            <CreditCard size={20} />
            <h2>{showSubscriptions ? 'Subscribe for More' : 'Acquire Scan Credits'}</h2>
          </div>
          <button className="stripe-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="stripe-modal-body">
          <div className="stripe-tabs">
            <button 
              className={`stripe-tab ${!showSubscriptions ? 'active' : ''}`}
              onClick={() => setShowSubscriptions(false)}
            >
              <Zap size={16} />
              One-Time Credits
            </button>
            <button 
              className={`stripe-tab ${showSubscriptions ? 'active' : ''}`}
              onClick={() => setShowSubscriptions(true)}
            >
              <Infinity size={16} />
              Subscriptions
            </button>
          </div>
          
          {loading ? (
            <div className="stripe-loading">
              <Loader2 size={32} className="spin" />
              <span>Loading packages...</span>
            </div>
          ) : (
            <>
              <p className="stripe-desc">
                {showSubscriptions 
                  ? 'Subscribe for monthly scans. Cancel anytime.' 
                  : 'Purchase credits for one-time use'}
              </p>

              <div className="stripe-packages">
                {(showSubscriptions ? subscriptionPlans : creditPackages).map((pkg) => (
                  <div
                    key={pkg.id}
                    className={`stripe-package ${pkg.popular ? 'popular' : ''}`}
                  >
                    {pkg.popular && (
                      <div className="popular-badge">
                        <Star size={12} />
                        Best Value
                      </div>
                    )}
                    <div className="package-header">
                      <h3>{pkg.name}</h3>
                      <div className="package-price">{pkg.price}</div>
                    </div>
                    <p className="package-desc">{pkg.description}</p>
                    <div className="package-credits">
                      {pkg.isUnlimited ? (
                        <>
                          <Infinity size={14} />
                          Unlimited scans
                        </>
                      ) : (
                        <>
                          <BoltIcon size={14} />
                          {pkg.scans} scans included
                        </>
                      )}
                    </div>
                    <button
                      className="package-btn"
                      onClick={() => handlePurchase(pkg.id)}
                      disabled={processing !== null}
                    >
                      {processing === pkg.id ? (
                        <>
                          <Loader2 size={16} className="spin" />
                          Redirecting...
                        </>
                      ) : (
                        <>
                          <CreditCard size={16} />
                          {showSubscriptions ? 'Subscribe' : 'Purchase'}
                        </>
                      )}
                    </button>
                  </div>
                ))}
              </div>

              {error && (
                <div className="stripe-error">
                  <X size={16} />
                  {error}
                </div>
              )}

              <div className="stripe-footer">
                <div className="stripe-security">
                  <Check size={14} />
                  <span>Secure checkout powered by Stripe</span>
                </div>
              </div>
            </>
          )}
        </div>

        <style>{`
          .stripe-modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 1rem;
            animation: fadeIn 0.2s ease;
          }

          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }

          .stripe-modal {
            width: 100%;
            max-width: 680px;
            background: linear-gradient(135deg, rgba(25, 15, 40, 0.98) 0%, rgba(15, 8, 25, 0.99) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            overflow: hidden;
            animation: slideUp 0.3s ease;
          }

          @keyframes slideUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
          }

          .stripe-modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.5rem 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
          }

          .stripe-modal-title {
            display: flex;
            align-items: center;
            gap: 12px;
            color: var(--color-primary);
          }

          .stripe-modal-title h2 {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--color-text);
          }

          .stripe-close {
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            color: var(--color-text-muted);
            cursor: pointer;
            transition: var(--transition);
          }

          .stripe-close:hover {
            background: rgba(252, 25, 53, 0.2);
            border-color: var(--color-danger);
            color: var(--color-danger);
          }

          .stripe-modal-body {
            padding: 2rem;
          }

          .stripe-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            padding: 4px;
          }

          .stripe-tab {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 0.75rem 1rem;
            background: transparent;
            border: none;
            border-radius: 10px;
            color: var(--color-text-muted);
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
          }

          .stripe-tab:hover {
            color: var(--color-text);
          }

          .stripe-tab.active {
            background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
            color: white;
          }

          .stripe-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
            padding: 3rem;
            color: var(--color-text-muted);
          }

          .spin {
            animation: spin 1s linear infinite;
          }

          @keyframes spin {
            to { transform: rotate(360deg); }
          }

          .stripe-desc {
            color: var(--color-text-muted);
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
            text-align: center;
          }

          .stripe-packages {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
          }

          .stripe-package {
            position: relative;
            padding: 1.5rem;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            text-align: center;
            transition: var(--transition);
          }

          .stripe-package:hover {
            border-color: rgba(255, 111, 55, 0.3);
            transform: translateY(-2px);
          }

          .stripe-package.popular {
            border-color: var(--color-primary);
            background: rgba(255, 111, 55, 0.05);
          }

          .popular-badge {
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 12px;
            background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
            border-radius: 100px;
            color: white;
            font-size: 0.7rem;
            font-weight: 700;
            white-space: nowrap;
          }

          .package-header {
            margin-bottom: 0.75rem;
          }

          .package-header h3 {
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--color-text-muted);
            margin-bottom: 0.5rem;
          }

          .package-price {
            font-size: 2rem;
            font-weight: 900;
            color: var(--color-text);
          }

          .package-desc {
            font-size: 0.8rem;
            color: var(--color-text-dim);
            margin-bottom: 1rem;
          }

          .package-credits {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 0.5rem 1rem;
            background: rgba(255, 111, 55, 0.1);
            border-radius: 100px;
            font-size: 0.8rem;
            color: var(--color-primary);
            margin-bottom: 1.25rem;
          }

          .package-btn {
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 0.875rem;
            background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
            transition: var(--transition-bounce);
            box-shadow: 0 4px 15px var(--color-primary-glow);
          }

          .package-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px var(--color-primary-glow);
          }

          .package-btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
          }

          .stripe-error {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 1rem;
            padding: 0.875rem 1rem;
            background: rgba(252, 25, 53, 0.1);
            border: 1px solid rgba(252, 25, 53, 0.2);
            border-radius: 10px;
            color: var(--color-danger);
            font-size: 0.85rem;
          }

          .stripe-footer {
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
          }

          .stripe-security {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            color: var(--color-text-dim);
            font-size: 0.8rem;
          }

          @media (max-width: 600px) {
            .stripe-packages {
              grid-template-columns: 1fr;
            }
            .stripe-modal {
              border-radius: 16px;
            }
            .stripe-modal-header,
            .stripe-modal-body {
              padding: 1.25rem;
            }
          }
        `}</style>
      </div>
    </div>
  )
}
