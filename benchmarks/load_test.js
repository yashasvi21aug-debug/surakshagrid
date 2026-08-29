import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 200 },  // Ramp up to 200 users
    { duration: '30s', target: 1000 }, // Peak load: 1,000 concurrent citizens
    { duration: '10s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200', 'p(99)<500'], // PRD NFR: 95th percentile <200ms
    http_req_failed: ['rate<0.01'],              // Error rate < 1%
  },
};

export default function () {
  const url = __ENV.BASE_URL ? `${__ENV.BASE_URL}/api/v1/sos/` : 'http://localhost:8000/api/v1/sos/';
  
  const categories = ['CRITICAL_TRAPPED', 'MEDICAL_EVAC', 'FOOD_WATER'];
  const category = categories[Math.floor(Math.random() * categories.length)];

  const payload = JSON.stringify({
    category: category,
    emergencyType: category,
    phone: `+91-98${Math.floor(10000000 + Math.random() * 90000000)}`,
    lat: 28.6321 + (Math.random() - 0.5) * 0.1,
    lng: 77.4446 + (Math.random() - 0.5) * 0.1,
    accuracy: 10,
    rainRate: 45.0,
    notes: 'k6 performance test synthetic payload',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(url, payload, params);

  check(res, {
    'status is 201': (r) => r.status === 201,
    'has incident id': (r) => JSON.parse(r.body).id !== undefined,
  });

  sleep(0.1);
}
