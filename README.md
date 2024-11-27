# Afrimeals

Afrimeals is an innovative AI-powered platform that provides personalized meal planning and nutritional insights, specifically tailored for the African diaspora. It aims to preserve traditional recipes while offering modern dietary solutions. Afrimeals integrates AfriGloss, an open-source cultural glossary, to enrich the user experience with deep cultural and culinary insights.

## Key Features

- **AI Meal Planning Engine**: Delivers personalized meal suggestions based on dietary preferences, cultural context, health goals, and budget.
- **Smart Recipe System**: Offers a comprehensive database of traditional and modern recipes, complete with ingredient substitutions, cooking instructions, and video tutorials.
- **Health and Nutrition Insights**: Tracks nutritional intake and health goals, providing dietary compliance and allergy management.
- **Smart Shopping and Delivery Integration**: Automates grocery lists, compares store availability and prices, and integrates with African grocery stores for delivery.

## AfriGloss Integration

AfriGloss is an integral part of Afrimeals, serving as an intelligent cultural glossary for African culinary terms. It enhances the meal planning experience by providing users with insights into ingredients, cooking techniques, and cultural nuances.

## Installation

To set up Afrimeals locally, follow these steps:

1. **Clone the repository**:

```bash
git clone https://github.com/yourusername/afrimeals.git
cd afrimeals
```
2. **Create a virtual environment and activate it**:
```bash
python3 -m venv venv
source venv/bin/activate
```
3. **Install the required packages**:
   ```bash
pip install -r requirements.txt
```
4. **Set up environment variables**:
 - Create a `.env` file in the project root and add your configuration:
   ```
   SECRET_KEY=your-django-secret-key
   DEBUG=True
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```
5. **Run migrations and start the server**:
 ```  bash
python manage.py migrate
python manage.py runserver
```
## Deployment

Afrimeals is designed for deployment on platforms like Render. For detailed deployment instructions, refer to the Render documentation.

## License

Afrimeals is a private project. However, AfriGloss, its cultural glossary component, is open-source and available under the MIT License. See the [Afrigloss repository](https://github.com/yourusername/afrigloss) for more details.

## Contributing

Contributions to Afrimeals are not currently accepted as it is a private project. However, contributions to AfriGloss are welcome and encouraged.

## Contact

For inquiries, please contact [your-email@example.com](mailto:your-email@example.com).

## AI Titans Network

Afrimeals is part of the AI Titans Network, a community initiative focused on AI education and empowerment. The network leverages Afrimeals and AfriGloss for educational activities, providing real-world examples in AI, ML, and NLP.
