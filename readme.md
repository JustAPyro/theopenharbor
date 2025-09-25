# The Open Harbor: Simple, Accessible File Sharing

Welcome to The Open Harbor\! We're a small team dedicated to creating a **simple, affordable file-sharing platform** built specifically for photographers, creative professionals, and small groups. Think of us as a cleaner, more focused alternative to Dropbox or Google Drive, prioritizing ease-of-use, beautiful galleries, and transparent pricing.

Our goal is to make managing and sharing your files—especially high-resolution photos—effortless.

-----

## Technical Details

We're a small, agile team, and we've partnered with **Cloudflare** for our file hosting infrastructure. This allows us to leverage their highly reputable and robust network to provide secure, fast, and reliable file storage at a fraction of the cost of building our own data centers. This partnership ensures that your files are handled by an industry leader while we focus on what matters most: building a great user experience.

-----

## Getting Started for Developers

We'd love for you to contribute\! Follow these steps to set up a local development server.

1.  **Virtual Environment (Recommended)**
    Start by creating a Python virtual environment to manage project dependencies.

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Dependencies**
    Install all required packages using pip.

    ```bash
    pip install -r .requirements.txt
    ```

3.  **Set Up Environment Variables**
    Copy the template file to create your local `.env` file, which is necessary for running the application.

    ```bash
    mv .env_template .env
    ```

4.  **Run the Server**
    You're ready to go\! Launch the development server.

    ```bash
    flask run
    ```

-----

## How to Contribute

We welcome contributions from everyone\! Whether you're a developer, designer, or just a user with a great idea, your input is valuable.

  * **Found a bug?** Check our issue tracker on GitHub to see if it has already been reported. If not, please open a new issue with a clear description and steps to reproduce the problem.
  * **Have an idea for a new feature?** We'd love to hear it\! Open a new feature request on our issue tracker.
  * **Want to contribute code?** After finding a bug or feature to work on, fork the repository, make your changes, and submit a pull request. We'll review your changes and work with you to get them merged.

Thank you for helping us build a better platform for file sharing\!
