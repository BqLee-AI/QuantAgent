import { createFileRoute } from '@tanstack/react-router'

import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'

export const Route = createFileRoute('/_app/(workspace)/skills/')({
  component: SkillsPage,
})

function SkillsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">技能</p>
        <h1 className="page-title">技能注册表</h1>
        <p className="page-description">
          查看可用技能、运行准备状态和后续执行使用情况。
        </p>
      </section>

      <section className="placeholder-grid" aria-label="技能总览">
        <PlaceholderPanel title="目录" copy="展示已注册技能及其能力元数据。" />
        <PlaceholderPanel title="准备状态" copy="检查依赖、权限和运行可用性。" />
        <PlaceholderPanel title="使用情况" copy="观察技能的使用分布和执行模式。" />
      </section>
    </>
  )
}
