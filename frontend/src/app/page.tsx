import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]"></div>

        <div className="relative mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <Badge className="mb-4 bg-purple-500/10 text-purple-300 border-purple-500/20">
              Powered by AI
            </Badge>

            <h1 className="text-5xl font-bold tracking-tight text-white sm:text-7xl mb-6">
              Discover the Next
              <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent"> Trending</span>
              <br />
              E-Commerce Stores
            </h1>

            <p className="text-lg leading-8 text-gray-300 mb-10">
              Get real-time insights into trending Shopify stores, track products, and discover emerging market opportunities before your competition.
            </p>

            <div className="flex items-center justify-center gap-4">
              <Link href="/auth/register">
                <Button size="lg" className="bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-700 hover:to-fuchsia-700">
                  Start Free Trial
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10">
                  View Dashboard
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to track e-commerce trends
            </h2>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              Powerful tools to help you discover, analyze, and capitalize on trending stores and products.
            </p>
          </div>

          <div className="mx-auto mt-16 max-w-7xl grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <div className="mb-4 text-4xl">🔥</div>
                <CardTitle>Trending Scores</CardTitle>
                <CardDescription>
                  AI-powered trending scores calculated from growth velocity, recency, and engagement metrics.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-4 text-4xl">📊</div>
                <CardTitle>Real-Time Analytics</CardTitle>
                <CardDescription>
                  Track product counts, revenue estimates, and traffic data updated in real-time.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-4 text-4xl">🔔</div>
                <CardTitle>Smart Alerts</CardTitle>
                <CardDescription>
                  Get notified when new stores match your criteria or when products drop in price.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-4 text-4xl">🎯</div>
                <CardTitle>Category Insights</CardTitle>
                <CardDescription>
                  Filter and discover stores across Fashion, Beauty, Electronics, and more categories.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-4 text-4xl">⭐</div>
                <CardTitle>Save Favorites</CardTitle>
                <CardDescription>
                  Bookmark interesting stores and add notes to track your research.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-4 text-4xl">🚀</div>
                <CardTitle>Growth Tracking</CardTitle>
                <CardDescription>
                  Monitor store growth rates and identify rapidly expanding businesses.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-violet-600 to-fuchsia-600">
        <div className="mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Ready to discover trending stores?
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-violet-100">
              Join thousands of entrepreneurs and researchers using TrendChecker to find their next opportunity.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link href="/auth/register">
                <Button size="lg" variant="secondary">
                  Get Started Free
                </Button>
              </Link>
              <Link href="/pricing">
                <Button size="lg" variant="ghost" className="text-white hover:bg-white/10">
                  View Pricing
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900">
        <div className="mx-auto max-w-7xl px-6 py-12 lg:px-8">
          <p className="text-center text-xs leading-5 text-gray-400">
            &copy; 2024 TrendChecker. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
