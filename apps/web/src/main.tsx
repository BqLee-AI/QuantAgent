import { bootstrapApp } from './app/bootstrap';
import './styles.css'

const container = document.getElementById('root');

if (!container) {
  throw new Error('Root container #root was not found.');
}

bootstrapApp(container);
