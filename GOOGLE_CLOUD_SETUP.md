# Google Cloud Project Setup for OAuth 2.0

This document provides step-by-step instructions to set up a Google Cloud Project for OAuth 2.0 authentication, which is necessary for the "Login with Google" feature.

## 1. Create or Select a Project

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  If you have an existing project you'd like to use, select it from the project dropdown at the top of the page.
3.  If you need to create a new project:
    *   Click on the project dropdown and then click "New Project".
    *   Enter a "Project name" (e.g., "My Web App Auth").
    *   Select an "Organization" and "Location" if applicable.
    *   Click "Create".

## 2. Enable the Google People API

1.  Once your project is selected, navigate to the "APIs & Services" > "Library" section from the left-hand navigation menu.
2.  In the search bar, type "Google People API" and select it from the results.
3.  Click the "Enable" button. If it's already enabled, you'll see a "Manage" button instead.

## 3. Configure the OAuth Consent Screen

1.  Go to "APIs & Services" > "OAuth consent screen" from the left-hand navigation menu.
2.  **User Type**:
    *   Choose "External" if your application will be used by any Google Account user.
    *   Choose "Internal" if your application is restricted to users within your Google Workspace organization (this requires a Google Workspace subscription).
    *   Click "Create".
3.  **App information**:
    *   **App name**: Enter the name of your application (e.g., "My Awesome Web App"). This is the name users will see.
    *   **User support email**: Select your email address for users to contact for support.
    *   **App logo**: Optionally, upload an app logo.
4.  **App domain**:
    *   **Application home page**: Enter the URL of your application's home page (e.g., `http://localhost:5000`).
    *   **Application privacy policy link**: Enter a link to your application's privacy policy. (You can use a placeholder for now if you don't have one, e.g., `http://localhost:5000/privacy`).
    *   **Application terms of service link**: Enter a link to your application's terms of service. (You can use a placeholder for now, e.g., `http://localhost:5000/terms`).
5.  **Authorized domains**:
    *   Click "+ Add Domain".
    *   Enter the domain(s) from which your application will be making OAuth requests. For local development, if you are using `localhost:5000`, you might not need to add `localhost` here explicitly as it's often implicitly trusted for development, but if you encounter issues, add your application's domain (e.g., `yourdomain.com` if deployed, or `localhost.com` if you've configured your hosts file for local development under a specific domain). For now, you can leave this blank or add `localhost` if you plan to use `http://localhost` for redirect URIs.
6.  **Developer contact information**:
    *   Enter your email address. This is for Google to contact you about your project.
7.  Click "Save and Continue".
8.  **Scopes**:
    *   Click "Add or Remove Scopes".
    *   You will need scopes to access user information. For basic login, common scopes are:
        *   `.../auth/userinfo.email` (to get the user's email address)
        *   `.../auth/userinfo.profile` (to get basic profile information like name and profile picture)
        *   `openid` (standard OpenID Connect scope)
    *   Select these scopes (you can search for them) and click "Update".
    *   Click "Save and Continue".
9.  **Test users** (Only if you selected "External" and your app is not yet published):
    *   Click "+ Add Users".
    *   Enter the Google email addresses of users who will be allowed to test your application before it's published.
    *   Click "Add".
    *   Click "Save and Continue".
10. **Summary**:
    *   Review your settings.
    *   Click "Back to Dashboard". Your app might be in "Testing" mode. You can publish it later by clicking "Publish App" on the OAuth consent screen page once you've verified everything and are ready for external users.

## 4. Create OAuth 2.0 Client ID Credentials

1.  Go to "APIs & Services" > "Credentials" from the left-hand navigation menu.
2.  Click "+ Create Credentials" at the top of the page and select "OAuth client ID".
3.  **Application type**: Select "Web application" from the dropdown.
4.  **Name**: Give your client ID a name (e.g., "Web Client 1").
5.  **Authorized JavaScript origins**:
    *   If your application uses JavaScript to handle the sign-in flow directly in the browser, add your application's origins here.
    *   For example, if you are running your app locally on port 5000, add `http://localhost:5000`.
    *   Click "+ Add URI".
6.  **Authorized redirect URIs**:
    *   These are the endpoints to which Google will redirect users after they have authenticated. This URI must exactly match one of the URIs you will specify in your application's code.
    *   Click "+ Add URI".
    *   For now, add the placeholder: `http://localhost:5000/login/google/authorized`. You will replace this with your actual redirect URI when you implement the OAuth flow in your application.
7.  Click "Create".
8.  A dialog box will appear showing your **Client ID** and **Client Secret**.
    *   **IMPORTANT**: Copy these values and store them securely. You will need them for your application's configuration.
    *   You can download the credentials as a JSON file as well.

## 5. Store Your Credentials Securely

*   The **Client ID** and **Client Secret** are sensitive. Do not commit them directly into your source code repository.
*   It is recommended to store them as environment variables:
    *   `GOOGLE_CLIENT_ID=YOUR_COPIED_CLIENT_ID`
    *   `GOOGLE_CLIENT_SECRET=YOUR_COPIED_CLIENT_SECRET`
*   Alternatively, you can use a `.env` file (make sure to add `.env` to your `.gitignore` file) to load these variables into your application's environment during development.

You have now configured your Google Cloud Project and obtained the necessary OAuth 2.0 credentials. These will be used by your application to authenticate users with their Google accounts.
