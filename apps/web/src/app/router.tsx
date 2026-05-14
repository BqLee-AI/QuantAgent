import {
  createRootRoute,
  createRouter,
} from '@tanstack/react-router';
import App from '../App';

const rootRoute = createRootRoute({
  component: App,
});

export function createAppRouter() {
  return createRouter({
    routeTree: rootRoute,
  });
}
