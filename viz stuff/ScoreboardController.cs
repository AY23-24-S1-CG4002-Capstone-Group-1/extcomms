using UnityEngine;
using TMPro;

public class ScoreboardController : MonoBehaviour
{
    public TMP_Text playerScoreText;
    public TMP_Text opponentScoreText;

    private int playerScore = 0;
    private int opponentScore = 0;

    // This assumes you have methods in your player's script that gets called when health reaches 0
    public void OnPlayerDeath()
    {
        opponentScore++;
        UpdateScoreText();
    }

    public void OnOpponentDeath()
    {
        playerScore++;
        UpdateScoreText();
    }

    private void UpdateScoreText()
    {
        playerScoreText.text = playerScore.ToString();
        opponentScoreText.text = opponentScore.ToString();
    }

    public void SetScore(int x, int y)
    {
        playerScore = x;
        opponentScore = y;
        UpdateScoreText();
    }
}

