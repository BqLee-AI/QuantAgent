import type { CreateModelProviderInput } from './api';

export interface ProviderPresetDefinition {
  id: string;
  name: string;
  description: string;
  draft: Omit<CreateModelProviderInput, 'enabled' | 'is_default'> & {
    example_model: string;
  };
}

export const providerPresets: ProviderPresetDefinition[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    description: '官方 OpenAI API',
    draft: {
      provider_type: 'openai_compatible',
      name: 'OpenAI',
      base_url: 'https://api.openai.com/v1',
      api_key: null,
      example_model: 'gpt-5.4',
    },
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    description: 'Anthropic OpenAI-compatible gateway',
    draft: {
      provider_type: 'openai_compatible',
      name: 'Anthropic',
      base_url: 'https://api.anthropic.com/v1',
      api_key: null,
      example_model: 'claude-sonnet-4-0',
    },
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    description: 'DeepSeek 官方接口',
    draft: {
      provider_type: 'openai_compatible',
      name: 'DeepSeek',
      base_url: 'https://api.deepseek.com/v1',
      api_key: null,
      example_model: 'deepseek-chat',
    },
  },
  {
    id: 'qwen',
    name: 'Qwen',
    description: '阿里云百炼 / Qwen 常见入口',
    draft: {
      provider_type: 'openai_compatible',
      name: 'Qwen',
      base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      api_key: null,
      example_model: 'qwen-plus',
    },
  },
  {
    id: 'moonshot',
    name: 'Moonshot',
    description: 'Moonshot / Kimi OpenAI-compatible',
    draft: {
      provider_type: 'openai_compatible',
      name: 'Moonshot',
      base_url: 'https://api.moonshot.cn/v1',
      api_key: null,
      example_model: 'moonshot-v1-8k',
    },
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    description: '多模型聚合网关',
    draft: {
      provider_type: 'openai_compatible',
      name: 'OpenRouter',
      base_url: 'https://openrouter.ai/api/v1',
      api_key: null,
      example_model: 'openai/gpt-4.1',
    },
  },
  {
    id: 'custom',
    name: '自定义',
    description: '自定义 OpenAI-compatible 网关',
    draft: {
      provider_type: 'openai_compatible',
      name: 'Custom Provider',
      base_url: '',
      api_key: null,
      example_model: 'custom-model',
    },
  },
];
