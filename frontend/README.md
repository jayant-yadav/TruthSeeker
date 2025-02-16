# Frontend

This is the frontend application built with React, TypeScript, and Vite.

## Prerequisites

- Node.js (v18 or higher recommended)
- npm or yarn package manager

## Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173` by default.

## Available Scripts

- `npm run dev` - Starts the development server with hot reload
- `npm run build` - Builds the application for production
- `npm run lint` - Runs ESLint to check code quality
- `npm run preview` - Previews the production build locally

## Development

This project uses:
- React 18 with TypeScript
- Vite as the build tool
- ESLint for code quality
- TypeScript for type safety

## ESLint Configuration

For production applications, we recommend enabling type-aware lint rules. See the [ESLint documentation](https://eslint.org/) for more details on configuration.

## Project Structure

```
frontend/
├── src/           # Source files
├── public/        # Static assets
├── index.html     # Entry HTML file
└── vite.config.ts # Vite configuration
```

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type aware lint rules:

- Configure the top-level `parserOptions` property like this:

```js
export default tseslint.config({
  languageOptions: {
    // other options...
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

- Replace `tseslint.configs.recommended` to `tseslint.configs.recommendedTypeChecked` or `tseslint.configs.strictTypeChecked`
- Optionally add `...tseslint.configs.stylisticTypeChecked`
- Install [eslint-plugin-react](https://github.com/jsx-eslint/eslint-plugin-react) and update the config:

```js
// eslint.config.js
import react from 'eslint-plugin-react'

export default tseslint.config({
  // Set the react version
  settings: { react: { version: '18.3' } },
  plugins: {
    // Add the react plugin
    react,
  },
  rules: {
    // other rules...
    // Enable its recommended rules
    ...react.configs.recommended.rules,
    ...react.configs['jsx-runtime'].rules,
  },
})
```
