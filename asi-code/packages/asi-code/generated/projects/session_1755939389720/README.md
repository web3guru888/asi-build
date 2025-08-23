# Modern Web Application with React, TypeScript, and Tailwind CSS

This project is a modern web application built with React, TypeScript, and Tailwind CSS, following best practices for scalable frontend development.

## Features

- ✅ React 18 with TypeScript
- ✅ Tailwind CSS for utility-first styling
- ✅ Vite as the build tool (fast development server and optimized builds)
- ✅ ESLint + Prettier for code quality and formatting
- ✅ Component-based architecture with reusable UI components
- ✅ GitHub Actions for CI/CD workflows
- ✅ Environment variable management
- ✅ Testing setup with Jest and React Testing Library
- ✅ Production-ready configuration

## Technologies Used

- **React** - Declarative JavaScript library for building user interfaces
- **TypeScript** - Strong typing for better developer experience and maintainability
- **Tailwind CSS** - Utility-first CSS framework for rapid UI development
- **Vite** - Next-generation frontend tooling for faster builds and HMR
- **ESLint** - Catch bugs and enforce code style standards
- **Prettier** - Opinionated code formatter for consistent style

## Getting Started

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn or pnpm

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd <project-directory>

# Install dependencies
npm install

# Create .env file from example
cp .env.example .env
```

### Development

```bash
# Start development server
npm run dev
```

### Build

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

### Testing

```bash
# Run tests
npm run test

# Run tests with coverage
npm run test:coverage
```

### Linting & Formatting

```bash
# Run ESLint
npm run lint

# Run Prettier
npm run format

# Check formatting
npm run format:check
```

## Project Structure

```
src/
├── components/     # Reusable UI components
├── pages/          # Route-level components
├── hooks/          # Custom React hooks
├── lib/            # Utility functions and services
├── types/          # TypeScript type definitions
├── assets/         # Static assets (images, fonts, etc.)
├── App.tsx         # Main application component
├── main.tsx        # Entry point
└── index.tsx       # Root ReactDOM render
```

## Environment Variables

Create a `.env` file in the root directory:

```env
VITE_API_URL=http://localhost:3000/api
VITE_APP_TITLE=My Modern Web App
NODE_ENV=development
```

See `.env.example` for all required environment variables.

## CI/CD

This project includes GitHub Actions workflows for:
- Continuous Integration (CI): runs tests and linting on every push/pull request
- Continuous Deployment (CD): deploys to production when merging to main branch

## Contributing

Please follow the code style enforced by ESLint and Prettier. Make sure all tests pass and code is formatted before submitting a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.