import {
  ListBox,
  Select,
} from '@heroui/react'

import type { EventAuditNodeFilter } from '../../types'

const filterOptions: Array<{ label: string; value: EventAuditNodeFilter }> = [
  { label: '全部节点', value: 'all' },
  { label: '只看建议变化', value: 'changes' },
  { label: '只看重分析', value: 'reanalysis' },
  { label: '只看人工动作', value: 'human' },
  { label: '只看系统节点', value: 'system' },
]

export function EventAuditNodeFilterPicker({
  value,
  onChange,
}: {
  value: EventAuditNodeFilter
  onChange: (value: EventAuditNodeFilter) => void
}) {
  const selectedOption = filterOptions.find((option) => option.value === value) ?? filterOptions[0]

  return (
    <Select
      aria-label="选择审计时间线范围"
      selectedKey={selectedOption.value}
      onSelectionChange={(key) => {
        if (key !== null) {
          onChange(String(key) as EventAuditNodeFilter)
        }
      }}
    >
      <Select.Trigger className="h-auto min-h-11 w-full rounded-2xl border-hairline bg-canvas px-3 py-2 shadow-none md:w-[200px]">
        <Select.Value>
          <div className="min-w-0 text-left">
            <span className="truncate text-[13px] font-bold text-foreground">
              {selectedOption.label}
            </span>
          </div>
        </Select.Value>
        <Select.Indicator />
      </Select.Trigger>
      <Select.Popover>
        <ListBox aria-label="选择审计时间线范围">
          {filterOptions.map((option) => (
            <ListBox.Item key={option.value} id={option.value} textValue={option.label}>
              <div className="py-1 text-[13px] font-bold text-foreground">{option.label}</div>
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  )
}
