import { expect, test } from '@playwright/experimental-ct-react';
import { PlaceholderPanel } from '@/app/components/PlaceholderPanel';

test('mounts shared UI components with the CT runner', async ({ mount }) => {
  const component = await mount(
    <PlaceholderPanel
      title="Incoming"
      copy="Captured events waiting for routing and analysis."
    />,
  );

  await expect(component.getByRole('heading', { name: 'Incoming' })).toBeVisible();
  await expect(component).toContainText('Captured events waiting for routing and analysis.');
});
