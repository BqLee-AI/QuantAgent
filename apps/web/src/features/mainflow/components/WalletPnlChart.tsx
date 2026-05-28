import { Card } from '@heroui/react'

import { walletTrend } from '../mock-data'

export function WalletPnlChart() {
  const maxMagnitude = Math.max(...walletTrend.map((item) => Math.abs(item.pnl)))

  return (
    <Card className="border border-[rgb(148_163_184_/_0.14)] bg-[linear-gradient(180deg,rgba(248,250,252,0.75),rgba(241,245,249,0.95))]">
      <div className="grid min-h-[132px] grid-cols-5 items-end gap-2 p-3 sm:min-h-[148px]">
        {walletTrend.map((item) => {
          const isNegative = item.pnl < 0
          const height = `${Math.max((Math.abs(item.pnl) / maxMagnitude) * 100, 18)}%`

          return (
            <div key={item.day} className="grid justify-items-center gap-1.5">
              <p className="m-0 text-[11px] font-bold text-muted-strong">
                {item.pnl > 0 ? '+' : '-'}¥ {Math.abs(item.pnl).toLocaleString('en-US')}
              </p>
              <div className="flex min-h-[76px] w-full items-end justify-center sm:min-h-[88px]">
                <div
                  className={isNegative
                    ? 'w-full max-w-6 rounded-t-lg rounded-b-sm bg-[linear-gradient(180deg,rgb(251,113,133),rgb(220,38,38))]'
                    : 'w-full max-w-6 rounded-t-lg rounded-b-sm bg-[linear-gradient(180deg,rgb(16,185,129),rgb(5,150,105))]'}
                  style={{ height }}
                />
              </div>
              <p className="m-0 text-[11px] font-bold text-muted">{item.day}</p>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
