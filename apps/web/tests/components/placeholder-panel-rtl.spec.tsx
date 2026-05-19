import { expect, test } from '@playwright/experimental-ct-react';
import * as matchers from '@testing-library/jest-dom/matchers';
import { PlaceholderPanel } from '@/app/components/PlaceholderPanel';
import { renderWithProviders } from '@/test/render';

expect.extend(matchers);

test('renders PlaceholderPanel through the shared RTL helper', async ({ mount }) => {
  const component = await renderWithProviders(
    mount,
    <PlaceholderPanel
      title="Incoming"
      copy="Captured events waiting for routing and analysis."
    />,
  );

  await expect(component.getByRole('heading', { name: 'Incoming' })).toBeVisible();
  await expect(component).toContainText(
    'Captured events waiting for routing and analysis.',
  );
});
